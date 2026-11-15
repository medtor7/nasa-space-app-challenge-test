# -*- coding: utf-8 -*-
"""Data pipeline of the Burning Activity Calendar (Google Colab notebook "nasa2", exported as .py).

ENGLISH SUMMARY (the comments and printed messages below are in Turkish)
This notebook produces every data file the app ships with, from the NASA FIRMS Area API:

  1. Download (cell "Hücre 1"): MODIS_SP 1 Nov 2000 - 2025 and VIIRS_SNPP_SP 2012 - 2025 for the
     bounding box 25.5-44.9 E, 35.7-42.2 N, in 5-day requests, one raw CSV per source and year
     (Google Drive: nasa_v2/raw/). Resumable: years already saved are skipped.
  2. Pipeline (cell "Hücre 2"):
       - filters: MODIS confidence >= 30 and type == 0; VIIRS confidence nominal/high and type == 0
       - 0.25 deg grid, daily counts per cell (raw_modis, raw_viirs)
       - monthly factors VIIRS/MODIS from the 2012-2025 overlap  -> monthly_factors_v2.json
       - Terra-only monthly factors (Terra detections only)     -> monthly_factors_terra_v2.json
       - intensity = VIIRS from 2012; MODIS x Terra-only factor before 4 July 2002 (Aqua start);
         MODIS x monthly factor from 4 July 2002 to 2011        -> daily_grid_v2.csv
       - weekly climatology, critical/core season, anomalies   -> summary_v2.json
  3. Figures fig1-fig4 (fig3 = Manavgat 2021 case study).
  4. Validation: three held-out schemes x three methods ("tek" single factor, "aylik" monthly factor,
     "us" = month coefficients + one shared exponent fitted in log space on regional monthly totals,
     with smearing)                                             -> validation_summary_v2.csv,
     yearly_ratio_v2.csv
  5. Checks: alternative counting measures (points, total FRP, cell-days), Terra vs. Aqua counts,
     small-area (1 deg) errors, the 2001 factors, and the Terra-only held-out test
     (Terra counts x Terra-only factors vs. Terra counts x Terra+Aqua factors).
  6. Day/night test (last cell): monthly factor (V0) vs. separate day and night monthly factors
     (V2) on the raw records, region and 1 deg blocks, three schemes, paired fold differences.
     The cell prints its results; they are transcribed in data/daynight_test_v2.csv,
     data/daynight_paired_v2.csv and data/daynight_factors_v2.csv.
  7. FRP-class test (last two cells): MODIS detections split into low / mid / high fire radiative power
     (33rd and 67th percentiles of the training years' MODIS FRP, recomputed in every fold), then
     V ~ sum of class counts x coefficients (V3a: 3 coefficients; V3b: 3 per season), non-negative least
     squares, fitted on 1 deg block-months or on regional monthly totals; compared with the monthly
     factor (V0). The second cell runs both fits. Printed results are transcribed in
     data/frp_test_v2.csv, data/frp_paired_v2.csv and data/frp_classes_v2.csv.

Requirements: a free NASA FIRMS MAP_KEY stored in Colab Secrets as FIRMS_KEY (it is never written
in this file), Google Drive, pandas, numpy, matplotlib, requests.
The repository's tools/ scripts re-check the outputs: tools/verify_validation_csv.py (validation
table), reference/verify_reference.js (season and anomalies), tools/compare_methods.py (methods).

AI/SI disclosure: parts of this notebook were written with the help of AI tools (Claude, Gemini);
the team ran it on the real FIRMS data.

Original file is located at
    https://colab.research.google.com/drive/1Da6wcVrJvy2pvKdAyQ0LV_dP-phbHrnE
"""

# Drive’ı bağlar, API fonksiyonunu tanımlar ve küçük bir test yapar.

import io, time, glob, requests
import pandas as pd
from google.colab import drive, userdata

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
import os; os.makedirs(OUT, exist_ok=True)

MAP_KEY = userdata.get('FIRMS_KEY')
BBOX = (25.5, 35.7, 44.9, 42.2)   # west, south, east, north

def fetch_range(source, start, end, bbox=BBOX, key=MAP_KEY, pause=0.3):
    w, s, e, n = bbox
    frames = []
    for d in pd.date_range(start, end, freq='5D'):
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
               f"{key}/{source}/{w},{s},{e},{n}/5/{d:%Y-%m-%d}")
        ok = False
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=60)
                if r.status_code == 200 and r.text.startswith('latitude'):
                    frames.append(pd.read_csv(io.StringIO(r.text)))
                    ok = True
                    break
                if r.status_code == 200 and len(r.text.strip()) == 0:
                    ok = True          # o aralıkta tespit yok
                    break
            except requests.RequestException:
                pass
            time.sleep(2)
        if not ok:
            print('BAŞARISIZ:', source, d.date())
        time.sleep(pause)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True).drop_duplicates()
    out = out[(out['acq_date'] >= str(pd.Timestamp(start).date())) &
              (out['acq_date'] <= str(pd.Timestamp(end).date()))]
    return out

# Küçük test
t1 = fetch_range('MODIS_SP', '2001-07-01', '2001-07-10')
t2 = fetch_range('MODIS_SP', '2023-01-01', '2023-01-31')
t3 = fetch_range('VIIRS_SNPP_SP', '2023-01-01', '2023-01-31')
for ad, t in (('MODIS 2001-07 (10 gün)', t1), ('MODIS 2023-01', t2), ('VIIRS 2023-01', t3)):
    print(ad, t.shape)
print(t2.columns.tolist())
print(t2.head(3).to_string())

# Karşılaştırma: eski CSV'lerdeki aynı ay ve aynı kutu
base = '/content/drive/MyDrive/nasa/'
def csv_count(folder, ay):
    d = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(base + folder + '/*.csv'))],
                  ignore_index=True)
    d = d[d['acq_date'].astype(str).str.startswith(ay)]
    return len(d[d['latitude'].between(35.7, 42.2) & d['longitude'].between(25.5, 44.9)])
print('Eski CSV MODIS 2023-01:', csv_count('modis', '2023-01'))
print('Eski CSV VIIRS 2023-01:', csv_count('viirs', '2023-01'))

import requests
from google.colab import userdata

key = userdata.get('FIRMS_KEY').strip()
print('Anahtar uzunluğu:', len(key), '(genelde 32 karakter olur)')

bbox = '25.5,35.7,44.9,42.2'
tests = {
    'MODIS_SP, 2023-01-01':      f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/MODIS_SP/{bbox}/5/2023-01-01',
    'VIIRS_SNPP_SP, 2023-01-01': f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/VIIRS_SNPP_SP/{bbox}/5/2023-01-01',
    'MODIS_NRT, en güncel':      f'https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/MODIS_NRT/{bbox}/1',
}
for ad, url in tests.items():
    try:
        r = requests.get(url, timeout=60)
        print('\n', ad, '-> durum:', r.status_code)
        print(r.text[:300].replace(key, '***'))
    except Exception as e:
        print('\n', ad, '-> HATA:', repr(e)[:300])

# anahtar hatalıysa baştan durup sebebini söylüyor ve bir istek başarısız olursa sunucunun mesajını yazdırıyor.

import io, time, glob, requests
import pandas as pd
from google.colab import drive, userdata

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
import os; os.makedirs(OUT, exist_ok=True)

MAP_KEY = userdata.get('FIRMS_KEY').strip()
print('Anahtar uzunluğu:', len(MAP_KEY))
if '/' in MAP_KEY or len(MAP_KEY) > 40:
    raise ValueError('Secrets içindeki değer bir anahtar gibi görünmüyor. '
                     'Sadece anahtarı yapıştırdığınızdan emin olun (bağlantı veya ek metin olmadan).')

BBOX = (25.5, 35.7, 44.9, 42.2)   # west, south, east, north

def fetch_range(source, start, end, bbox=BBOX, key=MAP_KEY, pause=0.3):
    w, s, e, n = bbox
    frames, hatalar = [], 0
    for d in pd.date_range(start, end, freq='5D'):
        url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
               f"{key}/{source}/{w},{s},{e},{n}/5/{d:%Y-%m-%d}")
        ok = False
        for attempt in range(3):
            try:
                r = requests.get(url, timeout=60)
                if r.status_code == 200 and r.text.startswith('latitude'):
                    frames.append(pd.read_csv(io.StringIO(r.text)))
                    ok = True
                    break
                if r.status_code == 200 and len(r.text.strip()) == 0:
                    ok = True          # o aralıkta tespit yok
                    break
                son_mesaj = f'durum {r.status_code}: {r.text[:120]}'.replace(key, '***')
            except requests.RequestException as ex:
                son_mesaj = repr(ex)[:120]
            time.sleep(2)
        if not ok:
            hatalar += 1
            if hatalar <= 3:
                print('BAŞARISIZ:', source, d.date(), '|', son_mesaj)
        time.sleep(pause)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True).drop_duplicates()
    out = out[(out['acq_date'] >= str(pd.Timestamp(start).date())) &
              (out['acq_date'] <= str(pd.Timestamp(end).date()))]
    return out

# Küçük test
t1 = fetch_range('MODIS_SP', '2001-07-01', '2001-07-10')
t2 = fetch_range('MODIS_SP', '2023-01-01', '2023-01-31')
t3 = fetch_range('VIIRS_SNPP_SP', '2023-01-01', '2023-01-31')
for ad, t in (('MODIS 2001-07 (10 gün)', t1), ('MODIS 2023-01', t2), ('VIIRS 2023-01', t3)):
    print(ad, t.shape)
print(t2.columns.tolist())
print(t2.head(3).to_string())

# Karşılaştırma: eski CSV'lerdeki aynı ay ve aynı kutu
base = '/content/drive/MyDrive/nasa/'
def csv_count(folder, ay):
    d = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(base + folder + '/*.csv'))],
                  ignore_index=True)
    d = d[d['acq_date'].astype(str).str.startswith(ay)]
    return len(d[d['latitude'].between(35.7, 42.2) & d['longitude'].between(25.5, 44.9)])
print('Eski CSV MODIS 2023-01:', csv_count('modis', '2023-01'))
print('Eski CSV VIIRS 2023-01:', csv_count('viirs', '2023-01'))

import glob
import pandas as pd

base = '/content/drive/MyDrive/nasa/'
keys = ['latitude', 'longitude', 'acq_date', 'acq_time']

def kontrol(api, folder, ay, ad):
    old = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(base + folder + '/*.csv'))],
                    ignore_index=True)
    old = old[old['acq_date'].astype(str).str.startswith(ay)]
    old = old[old['latitude'].between(35.7, 42.2) & old['longitude'].between(25.5, 44.9)]
    api_k = api[keys].drop_duplicates()
    m = old[keys].merge(api_k, on=keys, how='left', indicator=True)
    bulunan = (m['_merge'] == 'both').mean() * 100
    sadece_api = len(api_k) - (m['_merge'] == 'both').sum()
    print(f'{ad}: eski CSV satırlarının %{bulunan:.1f}\'i API sonucunda var | '
          f'sadece API\'de olan satır: {sadece_api}')

kontrol(t2, 'modis', '2023-01', 'MODIS 2023-01')
kontrol(t3, 'viirs', '2023-01', 'VIIRS 2023-01')

# Hücre 1: tam indirme (yeni hücre)
# 2000-2025 MODIS, 2012-2025 VIIRS, 5'er günlük parçalar halinde, toplam yaklaşık 2.900 istek.
# Her yıl bitince Drive’a (nasa_v2/raw/) kaydeder. Yarıda kesilirse hücreyi yeniden çalıştır, tamamlanan yılları atlayıp kaldığı yerden devam eder.

import io, os, time, requests
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
from google.colab import drive, userdata

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
RAW = OUT + 'raw/'
os.makedirs(RAW, exist_ok=True)

MAP_KEY = userdata.get('FIRMS_KEY').strip()
print('Anahtar uzunluğu:', len(MAP_KEY))
if '/' in MAP_KEY or len(MAP_KEY) > 40:
    raise ValueError('Secrets içindeki değer bir anahtar gibi görünmüyor.')

BBOX = (25.5, 35.7, 44.9, 42.2)   # west, south, east, north

def fetch_chunk(source, d):
    w, s, e, n = BBOX
    url = (f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
           f"{MAP_KEY}/{source}/{w},{s},{e},{n}/5/{d:%Y-%m-%d}")
    msg = ''
    for attempt in range(4):
        try:
            r = requests.get(url, timeout=90)
            txt = r.text
            if r.status_code == 200 and txt.startswith('latitude'):
                time.sleep(0.3)
                return pd.read_csv(io.StringIO(txt)), True, ''
            if r.status_code == 200 and len(txt.strip()) == 0:
                return pd.DataFrame(), True, ''
            msg = f'durum {r.status_code}: {txt[:100]}'.replace(MAP_KEY, '***')
            if r.status_code == 429 or 'exceed' in txt.lower() or 'limit' in txt.lower():
                time.sleep(60)
        except requests.RequestException as ex:
            msg = repr(ex)[:100]
        time.sleep(3 * (attempt + 1))
    return pd.DataFrame(), False, msg

def download_year(source, year, first_day=None):
    path = f'{RAW}{source}_{year}.csv'
    if os.path.exists(path):
        return 'zaten var', None
    start = pd.Timestamp(first_day) if first_day else pd.Timestamp(year, 1, 1)
    days = list(pd.date_range(start, pd.Timestamp(year, 12, 31), freq='5D'))
    with ThreadPoolExecutor(max_workers=4) as ex:
        results = list(ex.map(lambda d: fetch_chunk(source, d), days))
    bad = [(str(d.date()), m) for d, (_, ok, m) in zip(days, results) if not ok]
    if bad:
        return 'EKSİK (kaydedilmedi)', bad[:3]
    frames = [df for df, ok, m in results if len(df)]
    df = pd.concat(frames, ignore_index=True).drop_duplicates() if frames else pd.DataFrame()
    if len(df):
        df = df[df['acq_date'].astype(str).str[:4] == str(year)]
    df.to_csv(path, index=False)
    return 'tamam', len(df)

plan = ([('MODIS_SP', y, '2000-11-01' if y == 2000 else None) for y in range(2000, 2026)] +
        [('VIIRS_SNPP_SP', y, None) for y in range(2012, 2026)])

t0 = time.time()
for source, y, fd in plan:
    durum, ek = download_year(source, y, fd)
    print(f'{source} {y}: {durum} {ek if ek is not None else ""} | {int(time.time() - t0)} sn')

print('\nKaydedilen dosya sayısı:', len(os.listdir(RAW)), '(beklenen: 40)')

# Hücre 2: bütün hattı yeniden çalıştırma (Hücre 1 bitince)

import glob, json, os
import numpy as np
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
RAW = OUT + 'raw/'

def load(source):
    frames = []
    for f in sorted(glob.glob(f'{RAW}{source}_*.csv')):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            pass
    return pd.concat(frames, ignore_index=True)

modis = load('MODIS_SP')
viirs = load('VIIRS_SNPP_SP')
print('Ham satır (MODIS, VIIRS):', len(modis), len(viirs))

# 1) Temizlik: v1 ile aynı kurallar
for d in (modis, viirs):
    d['date'] = pd.to_datetime(d['acq_date'])
modis['confidence'] = pd.to_numeric(modis['confidence'], errors='coerce')
modis = modis[(modis['confidence'] >= 30) & (modis['type'] == 0)].copy()
viirs = viirs[viirs['confidence'].astype(str).str.lower().isin(['n', 'h', 'nominal', 'high'])
              & (viirs['type'] == 0)].copy()
print('Temizlik sonrası (MODIS, VIIRS):', len(modis), len(viirs))
# Terra’yı işaretle. Adım 1'de print('Temizlik sonrası (MODIS, VIIRS):', ...) satırının hemen altına ekle:
modis['terra'] = modis['satellite'].astype(str).str.lower().str.startswith('t')

# 2) 0,25° ızgara ve günlük özet
def add_cell(d, size=0.25):
    d['lat_c'] = (np.floor(d['latitude'] / size) * size + size / 2).round(3)
    d['lon_c'] = (np.floor(d['longitude'] / size) * size + size / 2).round(3)
    d['cell_id'] = d['lat_c'].astype(str) + '_' + d['lon_c'].astype(str)
    return d

def daily(d):
    return (d.groupby(['date', 'cell_id', 'lat_c', 'lon_c'])
              .agg(count=('frp', 'size'), frp_sum=('frp', 'sum')).reset_index())

m_daily = daily(add_cell(modis))
v_daily = daily(add_cell(viirs))

# 3) Aylık dönüşüm faktörü: önce eğitim/test doğrulaması
def monthly(d):
    d = d[d['date'].dt.year >= 2012]
    return d.groupby([d['date'].dt.year.rename('year'),
                      d['date'].dt.month.rename('month')])['count'].sum()

ov = pd.concat([monthly(m_daily).rename('M'), monthly(v_daily).rename('V')], axis=1).dropna().reset_index()
train = ov[ov['year'] <= 2018]
test = ov[ov['year'] >= 2019].copy()
k_single = train['V'].sum() / train['M'].sum()
g = train.groupby('month')[['M', 'V']].sum()
k_month = g['V'] / g['M']
test['pred_single'] = test['M'] * k_single
test['pred_month'] = test['M'] * test['month'].map(k_month)

def report(col):
    wape = (test[col] - test['V']).abs().sum() / test['V'].sum() * 100
    return round(wape, 1), round(test[col].corr(test['V']), 3)

print('\nTek faktör', round(k_single, 2), '(hata %, korelasyon):', report('pred_single'))
print('Aylık faktör (hata %, korelasyon):', report('pred_month'))

# 4) Nihai faktörler (2012-2025) ve birleşik seri
g_all = ov.groupby('month')[['M', 'V']].sum()
k_final = g_all['V'] / g_all['M']
print('\nAylık faktörler:'); print(k_final.round(2).to_dict())

# Yalnız-Terra faktörünü hesapla. Adım 4'te print('\nAylık faktörler:'); print(k_final.round(2).to_dict()) satırının hemen altına ekle:
mt = modis[modis['terra'] & (modis['date'].dt.year >= 2012)]
T = (mt.groupby([mt['date'].dt.year.rename('year'), mt['date'].dt.month.rename('month')])
       .size().rename('T').reset_index())
g_t = ov.merge(T, on=['year', 'month']).groupby('month')[['T', 'V']].sum()
k_terra = g_t['V'] / g_t['T']
assert len(k_terra) == 12, 'Terra faktörü 12 ayın hepsinde yok'   # eklenen kontrol
print('Terra faktörleri:', k_terra.round(2).to_dict())
k_terra.round(3).to_json(OUT + 'monthly_factors_terra_v2.json')

mm = m_daily.rename(columns={'count': 'raw_modis'})[['date', 'cell_id', 'lat_c', 'lon_c', 'raw_modis']]
vv = v_daily.rename(columns={'count': 'raw_viirs'})[['date', 'cell_id', 'lat_c', 'lon_c', 'raw_viirs']]
grid = mm.merge(vv, on=['date', 'cell_id', 'lat_c', 'lon_c'], how='outer')
grid[['raw_modis', 'raw_viirs']] = grid[['raw_modis', 'raw_viirs']].fillna(0)
grid['year'] = grid['date'].dt.year
grid['month'] = grid['date'].dt.month

# intensity satırını değiştir. Şu iki satırı sil:
# grid['intensity'] = np.where(grid['year'] >= 2012, grid['raw_viirs'],
                             # grid['raw_modis'] * grid['month'].map(k_final)).round(2)

# Yerine şunu yapıştır:
AQUA_BASLANGIC = pd.Timestamp('2002-07-04')   # Aqua verisinin ilk günü
# eklenen kontrol: bu tarihten önce Aqua tespiti olmamalı
assert (modis.loc[~modis['terra'], 'date'] >= AQUA_BASLANGIC).all(), 'Aqua başlangıç tarihi yanlış'
grid['intensity'] = np.where(
    grid['year'] >= 2012, grid['raw_viirs'],
    np.where(grid['date'] < AQUA_BASLANGIC,
             grid['raw_modis'] * grid['month'].map(k_terra),   # yalnız Terra dönemi
             grid['raw_modis'] * grid['month'].map(k_final))   # Terra + Aqua dönemi
).round(2)

out = grid.rename(columns={'lat_c': 'lat', 'lon_c': 'lon'})
out['date'] = out['date'].dt.strftime('%Y-%m-%d')
out = out[['date', 'cell_id', 'lat', 'lon', 'intensity', 'raw_modis', 'raw_viirs']]
out.to_csv(OUT + 'daily_grid_v2.csv', index=False)
k_final.round(3).to_json(OUT + 'monthly_factors_v2.json')
print('\ndaily_grid_v2:', out.shape, round(os.path.getsize(OUT + 'daily_grid_v2.csv') / 1e6, 1), 'MB')
print('Enlem aralığı:', out['lat'].min(), out['lat'].max(),
      '| Boylam aralığı:', out['lon'].min(), out['lon'].max())

# 5) Anomali ve sezon analizi (v1'in son hali)
df = grid.rename(columns={'lat_c': 'lat', 'lon_c': 'lon'})

def weekly_matrix(d, y0=2003, y1=2025):
    d = d[(d['date'].dt.year >= y0) & (d['date'].dt.year <= y1)].copy()
    d['yr'] = d['date'].dt.year
    d['week'] = ((d['date'].dt.dayofyear - 1) // 7).clip(upper=51)
    m = d.pivot_table(index='yr', columns='week', values='intensity', aggfunc='sum', fill_value=0)
    return m.reindex(index=range(y0, y1 + 1), columns=range(52), fill_value=0)

def analyze(d, z_thr=2.0, min_int=20, y0=2003, y1=2025):
    m = weekly_matrix(d, y0, y1)
    L = np.log1p(m)
    z = ((L - L.mean()) / L.std().replace(0, np.nan)).fillna(0)
    clim = np.expm1(L.mean()).rolling(3, center=True, min_periods=1).mean()
    an = [(int(y), int(w), round(float(m.loc[y, w]), 1), round(float(z.loc[y, w]), 2))
          for y in m.index for w in m.columns
          if z.loc[y, w] >= z_thr and m.loc[y, w] >= min_int]
    an.sort(key=lambda t: -t[3])
    return m, z, clim, an

def tiers(clim, ext=0.5, core=0.75):
    peak = clim.max()
    f = lambda t: [int(w) for w in clim.index[clim >= t * peak]] if peak > 0 else []
    return f(ext), f(core)

def wk(w):
    s = pd.Timestamp('2021-01-01') + pd.Timedelta(days=7 * int(w))
    return f"{s:%d %b}-{(s + pd.Timedelta(days=6)):%d %b}"

m_, z_, clim_, an_ = analyze(df)
crit, core = tiers(clim_)
print('\nKritik haftalar (geniş):', crit, '| v1: [24, 25, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41]')
print('Çekirdek haftalar:', core, '| v1: [34, 35, 36, 37, 38]')
print('Anomali sayısı:', len(an_), '| v1: 16')
for a in an_[:10]:
    print(a[0], wk(a[1]), '| yoğunluk', a[2], '| z', a[3])

summary = {'baseline_years': [2003, 2025],
           'weekly_climatology': clim_.round(2).tolist(),
           'critical_weeks': crit, 'core_weeks': core,
           'anomalies': [{'year': y, 'week': w, 'intensity': i, 'z': zz} for y, w, i, zz in an_]}
json.dump(summary, open(OUT + 'summary_v2.json', 'w'))

# 6) Manavgat kontrolü (Antalya kutusu)
box = df[df['lat'].between(36.0, 37.5) & df['lon'].between(30.0, 32.5)]
m2, z2, clim2, an2 = analyze(box)
ext2, core2 = tiers(clim2)
print('\nAntalya geniş:', [wk(w) for w in ext2])
print('Antalya çekirdek:', [wk(w) for w in core2])
for a in an2:
    if a[0] == 2021:
        print(a[0], wk(a[1]), '| yoğunluk', a[2], '| z', a[3])

# Şekilleri v2 için yeniden üretme

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from google.colab import drive

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'

# 0) Ham veri kontrolü: API testindeki sayılarla aynı olmalı
for src, beklenen in (('MODIS_SP', 1080), ('VIIRS_SNPP_SP', 4897)):
    r = pd.read_csv(f'{OUT}raw/{src}_2023.csv')
    print(src, 'Ocak 2023 satır:', int(r['acq_date'].astype(str).str.startswith('2023-01').sum()),
          '| beklenen:', beklenen)

df = pd.read_csv(OUT + 'daily_grid_v2.csv', parse_dates=['date'])
k_final = pd.read_json(OUT + 'monthly_factors_v2.json', typ='series')
k_final.index = k_final.index.astype(int)

# Şekil 1: önce / sonra
yr = df.assign(year=df['date'].dt.year).groupby('year')[['raw_modis', 'raw_viirs', 'intensity']].sum()
fig, ax = plt.subplots(1, 2, figsize=(14, 4))
yr[['raw_modis', 'raw_viirs']].replace(0, np.nan).plot(ax=ax[0], marker='o')
ax[0].set_title('Önce: ham sensör kayıtları')
yr['intensity'].plot(ax=ax[1], marker='o', color='green')
ax[1].set_title('Sonra: harmonize tek seri')
for a in ax:
    a.axvspan(1999.5, 2002.5, color='gray', alpha=0.2)
ax[1].text(2000, ax[1].get_ylim()[1] * 0.9, 'eksik/tek\nuydu dönemi', fontsize=9)
plt.tight_layout(); plt.savefig(OUT + 'fig1_v2_before_after.png', dpi=150); plt.show()

# Şekil 2: aylık faktörler
fig, ax = plt.subplots(figsize=(8, 3.5))
k_final.plot.bar(ax=ax, color='steelblue')
ax.axhline(k_final.mean(), ls='--', color='gray')
ax.set_title('Aylık dönüşüm faktörü (VIIRS / MODIS)'); ax.set_xlabel('Ay')
plt.tight_layout(); plt.savefig(OUT + 'fig2_v2_monthly_factors.png', dpi=150); plt.show()

# Şekil 4: test dönemi (2012-2018 eğitim, 2019-2025 test)
d = df[df['date'].dt.year >= 2012]
ov = (d.groupby([d['date'].dt.year.rename('year'), d['date'].dt.month.rename('month')])
        [['raw_modis', 'raw_viirs']].sum().reset_index()
        .rename(columns={'raw_modis': 'M', 'raw_viirs': 'V'}))
train = ov[ov['year'] <= 2018]
test = ov[ov['year'] >= 2019].copy()
k_single = train['V'].sum() / train['M'].sum()
g = train.groupby('month')[['M', 'V']].sum()
k_month = g['V'] / g['M']
test['pred_single'] = test['M'] * k_single
test['pred_month'] = test['M'] * test['month'].map(k_month)
test['tarih'] = pd.to_datetime(dict(year=test['year'], month=test['month'], day=1))
for col, ad in (('pred_single', 'Tek faktör'), ('pred_month', 'Aylık faktör')):
    print(ad, 'hata %:', round((test[col] - test['V']).abs().sum() / test['V'].sum() * 100, 1),
          '(beklenen: 22.7 ve 17.9)')
fig, ax = plt.subplots(figsize=(12, 4))
ax.plot(test['tarih'], test['V'], color='black', lw=2, label='Gerçek VIIRS')
ax.plot(test['tarih'], test['pred_single'], color='orange', label='Tek faktörle tahmin')
ax.plot(test['tarih'], test['pred_month'], color='green', label='Aylık faktörle tahmin')
ax.set_title("Test dönemi 2019-2025: gerçek VIIRS ve MODIS'ten tahmin")
ax.set_ylabel('Aylık yangın noktası sayısı'); ax.legend()
plt.tight_layout(); plt.savefig(OUT + 'fig4_v2_test_period.png', dpi=150); plt.show()

# Şekil 3: Manavgat 2021 (Antalya kutusu)
def weekly_matrix(d, y0=2003, y1=2025):
    d = d[(d['date'].dt.year >= y0) & (d['date'].dt.year <= y1)].copy()
    d['yr'] = d['date'].dt.year
    d['week'] = ((d['date'].dt.dayofyear - 1) // 7).clip(upper=51)
    m = d.pivot_table(index='yr', columns='week', values='intensity', aggfunc='sum', fill_value=0)
    return m.reindex(index=range(y0, y1 + 1), columns=range(52), fill_value=0)

box = df[df['lat'].between(36.0, 37.5) & df['lon'].between(30.0, 32.5)]
m2 = weekly_matrix(box)
L2 = np.log1p(m2)
z2 = ((L2 - L2.mean()) / L2.std().replace(0, np.nan)).fillna(0)
clim2 = np.expm1(L2.mean()).rolling(3, center=True, min_periods=1).mean()

w21 = m2.loc[2021]
colors = ['red' if (z2.loc[2021, w] >= 2 and w21[w] >= 20) else 'steelblue' for w in w21.index]
fig, ax = plt.subplots(figsize=(12, 4))
ax.bar(w21.index, w21.values, color=colors)
ax.plot(clim2.index, clim2.values, 'k-', lw=2, label='2003-2025 tipik değer')
ax.set_yscale('symlog', linthresh=10)
ax.annotate('Manavgat yangını\n(28 Temmuz)', xy=(30, w21[30]), xytext=(37, 600),
            arrowprops=dict(arrowstyle='->'))
ax.set_title('Antalya 2021: haftalık yangın yoğunluğu (kırmızı = anomali, log eksen)')
ax.set_xlabel('Yılın haftası (0 = 1-7 Ocak)'); ax.legend()
plt.tight_layout(); plt.savefig(OUT + 'fig3_v2_manavgat_2021.png', dpi=150); plt.show()

import os
print(sorted(os.listdir('/content/drive/MyDrive/nasa_v2/')))

# Aynı veri ve aynı eğitim/test ayrımıyla (2012-2018 öğren, 2019-2025 test et) dört ölçüyü tek kodla hesaplıyor: R², MAE, bias ve WAPE.
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
df = pd.read_csv(OUT + 'daily_grid_v2.csv', parse_dates=['date'])

d = df[df['date'].dt.year >= 2012]
ov = (d.groupby([d['date'].dt.year.rename('year'), d['date'].dt.month.rename('month')])
        [['raw_modis', 'raw_viirs']].sum().reset_index()
        .rename(columns={'raw_modis': 'M', 'raw_viirs': 'V'}))
train = ov[ov['year'] <= 2018]
test = ov[ov['year'] >= 2019].copy()

g = train.groupby('month')[['M', 'V']].sum()
k_month_tr = g['V'] / g['M']
k_single_tr = train['V'].sum() / train['M'].sum()
g_all = ov.groupby('month')[['M', 'V']].sum()
k_month_all = g_all['V'] / g_all['M']

def metrics(pred, act):
    sse = ((act - pred) ** 2).sum()
    sst = ((act - act.mean()) ** 2).sum()
    return {'R2': round(1 - sse / sst, 3),
            'MAE': round((act - pred).abs().mean()),
            'bias_%': round((pred.sum() - act.sum()) / act.sum() * 100, 1),
            'WAPE_%': round((act - pred).abs().sum() / act.sum() * 100, 1)}

act = test['V']
rows = {
    'Tek faktör (2012-2018, held-out)': metrics(test['M'] * k_single_tr, act),
    'Aylık faktör (2012-2018, held-out)': metrics(test['M'] * test['month'].map(k_month_tr), act),
    'Aylık faktör (tüm dönemden, HELD-OUT DEĞİL)': metrics(test['M'] * test['month'].map(k_month_all), act),
}
print(pd.DataFrame(rows).T)
print('Test aylarındaki ortalama VIIRS:', round(act.mean()))

import numpy as np
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
df = pd.read_csv(OUT + 'daily_grid_v2.csv', parse_dates=['date'])

# Aylık toplamlar (2012-2025, iki sensörün çakıştığı dönem)
d = df[df['date'].dt.year >= 2012]
ov = (d.groupby([d['date'].dt.year.rename('year'), d['date'].dt.month.rename('month')])
        [['raw_modis', 'raw_viirs']].sum().reset_index()
        .rename(columns={'raw_modis': 'M', 'raw_viirs': 'V'}))

# 1) Yıllık VIIRS / MODIS oranı
yr = ov.groupby('year')[['M', 'V']].sum()
yr['oran'] = (yr['V'] / yr['M']).round(2)
print(yr)
print('2012-2018 ortalama oran:', round(yr.loc[:2018, 'V'].sum() / yr.loc[:2018, 'M'].sum(), 2))
print('2019-2025 ortalama oran:', round(yr.loc[2019:, 'V'].sum() / yr.loc[2019:, 'M'].sum(), 2))

# 2) Üç yöntem
def fit_predict(train, test, method):
    if method == 'tek':
        return test['M'] * (train['V'].sum() / train['M'].sum())
    if method == 'aylik':
        g = train.groupby('month')[['M', 'V']].sum()
        return test['M'] * test['month'].map(g['V'] / g['M'])
    # 'us': ay başına katsayı + ortak üs (log uzayında), sadece deneme
    def X(t):
        dm = pd.get_dummies(t['month']).reindex(columns=range(1, 13), fill_value=0).astype(float).values
        return np.column_stack([dm, np.log1p(t['M'].values)])
    y = np.log1p(train['V'].values)
    beta, *_ = np.linalg.lstsq(X(train), y, rcond=None)
    smear = np.mean(np.exp(y - X(train) @ beta))
    pred = np.clip(np.exp(X(test) @ beta) * smear - 1, 0, None)
    return pd.Series(pred, index=test.index)

def metrics(pred, act):
    return {'WAPE_%': round((act - pred).abs().sum() / act.sum() * 100, 1),
            'bias_%': round((pred.sum() - act.sum()) / act.sum() * 100, 1)}

yillar = sorted(ov['year'].unique())
def sabit():
    yield ov[ov['year'] <= 2018], ov[ov['year'] >= 2019]
def ileri():
    for y in range(2015, 2026):
        yield ov[ov['year'] < y], ov[ov['year'] == y]
def birini_disarida():
    for y in yillar:
        yield ov[ov['year'] != y], ov[ov['year'] == y]

# 3) Üç doğrulama şeması x üç yöntem
sonuc = {}
for sema, ad in ((sabit, '1) Sabit: 2012-2018 -> 2019-2025'),
                 (ileri, '2) Ileriye genisleyen pencere (2015-2025)'),
                 (birini_disarida, '3) Her yili sirayla disarida birak')):
    for m in ('tek', 'aylik', 'us'):
        preds, acts = [], []
        for tr, te in sema():
            preds.append(fit_predict(tr, te, m))
            acts.append(te['V'])
        sonuc[(ad, m)] = metrics(pd.concat(preds), pd.concat(acts))

val = pd.DataFrame(sonuc).T
val.index.names = ['sema', 'yontem']
print()
print(val)

# 4) B için dosyalar
val.reset_index().to_csv(OUT + 'validation_summary_v2.csv', index=False)
yr.reset_index().to_csv(OUT + 'yearly_ratio_v2.csv', index=False)
print('\nKaydedildi: validation_summary_v2.csv ve yearly_ratio_v2.csv')

# Ham API dosyalarından aynı filtrelerle (güven ve type == 0) üç ölçüyü yeniden hesaplar ve iki şeye bakar:
# yıllık oranın dalgalanması ve sabit bölünmede (2012-2018 → 2019-2025) aylık faktörle held-out hata.

import glob
import numpy as np
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
RAW = '/content/drive/MyDrive/nasa_v2/raw/'

def load(source):
    frames = []
    for f in sorted(glob.glob(f'{RAW}{source}_*.csv')):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            pass
    return pd.concat(frames, ignore_index=True)

modis = load('MODIS_SP')
viirs = load('VIIRS_SNPP_SP')
modis['confidence'] = pd.to_numeric(modis['confidence'], errors='coerce')
modis = modis[(modis['confidence'] >= 30) & (modis['type'] == 0)].copy()
viirs = viirs[viirs['confidence'].astype(str).str.lower().isin(['n', 'h', 'nominal', 'high'])
              & (viirs['type'] == 0)].copy()
print('Temiz tespit sayısı:', len(modis), len(viirs), '(beklenen: 284313 590023)')

def aylik(d, ad):
    d = d.copy()
    d['date'] = pd.to_datetime(d['acq_date'])
    d = d[d['date'].dt.year.between(2012, 2025)]
    d['year'] = d['date'].dt.year
    d['month'] = d['date'].dt.month
    d['cell'] = (np.floor(d['latitude'] / 0.25).astype(int).astype(str) + '_' +
                 np.floor(d['longitude'] / 0.25).astype(int).astype(str))
    pts = d.groupby(['year', 'month']).size().rename(ad + '_nokta')
    frp = d.groupby(['year', 'month'])['frp'].sum().rename(ad + '_frp')
    cd = d.drop_duplicates(['cell', 'acq_date']).groupby(['year', 'month']).size().rename(ad + '_hucregun')
    return pd.concat([pts, frp, cd], axis=1)

ov = pd.concat([aylik(modis, 'M'), aylik(viirs, 'V')], axis=1).dropna().reset_index()
olcular = (('Nokta sayısı', 'nokta'), ('Toplam FRP', 'frp'), ('Hücre-gün', 'hucregun'))

# 1) Yıllık oranın dalgalanması
yr = ov.groupby('year').sum(numeric_only=True)
a = {}
for ad, k in olcular:
    oran = yr['V_' + k] / yr['M_' + k]
    a[ad] = {'ort. oran': round(oran.mean(), 2), 'min': round(oran.min(), 2),
             'max': round(oran.max(), 2), 'dalgalanma_%': round(oran.std() / oran.mean() * 100, 1)}
print('\nYıllık VIIRS/MODIS oranı (v2):')
print(pd.DataFrame(a).T)

# 2) Aylık faktörle held-out hata (2012-2018 -> 2019-2025)
train = ov[ov['year'] <= 2018]
test = ov[ov['year'] >= 2019]
b = {}
for ad, k in olcular:
    g = train.groupby('month')[['M_' + k, 'V_' + k]].sum()
    f = g['V_' + k] / g['M_' + k]
    pred = test['M_' + k] * test['month'].map(f)
    act = test['V_' + k]
    b[ad] = {'WAPE_%': round((act - pred).abs().sum() / act.sum() * 100, 1),
             'bias_%': round((pred.sum() - act.sum()) / act.sum() * 100, 1)}
print('\nAylık faktörle held-out hata (sabit bölünme):')
print(pd.DataFrame(b).T)

import glob
import numpy as np
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
RAW = '/content/drive/MyDrive/nasa_v2/raw/'

def load(source):
    frames = []
    for f in sorted(glob.glob(f'{RAW}{source}_*.csv')):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            pass
    return pd.concat(frames, ignore_index=True)

modis = load('MODIS_SP')
viirs = load('VIIRS_SNPP_SP')
modis['confidence'] = pd.to_numeric(modis['confidence'], errors='coerce')
modis = modis[(modis['confidence'] >= 30) & (modis['type'] == 0)].copy()
viirs = viirs[viirs['confidence'].astype(str).str.lower().isin(['n', 'h', 'nominal', 'high'])
              & (viirs['type'] == 0)].copy()
print('Temiz tespit sayısı:', len(modis), len(viirs), '(beklenen: 284313 590023)')

for d in (modis, viirs):
    d['date'] = pd.to_datetime(d['acq_date'])
    d['year'] = d['date'].dt.year
    d['month'] = d['date'].dt.month
print('Uydu değerleri:', modis['satellite'].unique())
modis['terra'] = modis['satellite'].astype(str).str.lower().str.startswith('t')

# 1) 2000-2006: hangi uydu kaç tespit gördü?
etiket = modis['terra'].map({True: 'Terra', False: 'Aqua'})
print(modis.groupby(['year', etiket]).size().unstack(fill_value=0).loc[2000:2006])
print('Terra ilk tarih:', modis.loc[modis['terra'], 'date'].min().date())
print('Aqua ilk tarih:', modis.loc[~modis['terra'], 'date'].min().date())

# 2) Terra'nın MODIS içindeki payı (2003-2025)
print('\nTerra payı:', modis.groupby('year')['terra'].mean().round(2).loc[2003:].to_dict())

# 3) Held-out test: tüm MODIS ve sadece Terra (2012-2018 -> 2019-2025)
def aylik(d, ad):
    d = d[d['year'].between(2012, 2025)]
    return d.groupby(['year', 'month']).size().rename(ad)

ov = pd.concat([aylik(modis, 'M'), aylik(modis[modis['terra']], 'T'), aylik(viirs, 'V')],
               axis=1).dropna().reset_index()
train = ov[ov['year'] <= 2018]
test = ov[ov['year'] >= 2019]
print('\nHeld-out test:')
for ad, col in (('MODIS (Terra+Aqua)', 'M'), ('Sadece Terra', 'T')):
    g = train.groupby('month')[[col, 'V']].sum()
    f = g['V'] / g[col]
    pred = test[col] * test['month'].map(f)
    act = test['V']
    print(ad, '| WAPE %:', round((act - pred).abs().sum() / act.sum() * 100, 1),
          '| bias %:', round((pred.sum() - act.sum()) / act.sum() * 100, 1))
    print('  faktörler:', f.round(2).to_dict())

import numpy as np
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
df = pd.read_csv(OUT + 'daily_grid_v2.csv', parse_dates=['date'])
d = df[df['date'].dt.year.between(2012, 2025)].copy()
d['year'] = d['date'].dt.year
d['month'] = d['date'].dt.month
d['blok'] = (np.floor(d['lat']).astype(int).astype(str) + '_' +
             np.floor(d['lon']).astype(int).astype(str))
bm = (d.groupby(['blok', 'year', 'month'])[['raw_modis', 'raw_viirs']].sum()
        .reset_index().rename(columns={'raw_modis': 'M', 'raw_viirs': 'V'}))

train = bm[bm['year'] <= 2018]
test = bm[bm['year'] >= 2019].copy()
g = train.groupby('month')[['M', 'V']].sum()
k = g['V'] / g['M']
test['P'] = test['M'] * test['month'].map(k)
test['err'] = (test['P'] - test['V']).abs()

reg = test.groupby(['year', 'month'])[['V', 'P']].sum()
print('Bölge, aylık (WAPE %, bias %):',
      round((reg['P'] - reg['V']).abs().sum() / reg['V'].sum() * 100, 1),
      round((reg['P'].sum() - reg['V'].sum()) / reg['V'].sum() * 100, 1), '(beklenen 17.9 ve 7.6)')
print('1° kareler, aylık, birleşik WAPE %:', round(test['err'].sum() / test['V'].sum() * 100, 1))

blk = test.groupby('blok')[['V', 'P', 'err']].sum()
blk['ort_aylik_V'] = blk['V'] / 84
blk['bias_%'] = (blk['P'] - blk['V']) / blk['V'].replace(0, np.nan) * 100
blk['grup'] = pd.cut(blk['ort_aylik_V'], [0, 20, 100, 500, 1e9],
                     labels=['<20', '20-100', '100-500', '>500'], include_lowest=True)
t = blk.groupby('grup', observed=True)[['V', 'P', 'err']].sum()
t['blok_sayisi'] = blk.groupby('grup', observed=True).size()
t['WAPE_%'] = (t['err'] / t['V'] * 100).round(1)
print('\nKarenin ortalama aylık VIIRS sayısına göre hata:')
print(t[['blok_sayisi', 'WAPE_%']])
print('\nBüyük karelerde (ort. aylık > 100) kare bazlı toplam bias dağılımı (%):')
print(blk.loc[blk['ort_aylik_V'] > 100, 'bias_%'].describe().round(1))

import json
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
OUT = '/content/drive/MyDrive/nasa_v2/'
g = pd.read_csv(OUT + 'daily_grid_v2.csv', parse_dates=['date'])
x = g[(g['date'].dt.year == 2001) & (g['raw_modis'] > 0)].copy()
x['oran'] = x['intensity'] / x['raw_modis']
x['ay'] = x['date'].dt.month
print('2001 satırlarında intensity / raw_modis (aya göre medyan):')
print(x.groupby('ay')['oran'].median().round(1).to_dict())
print('Terra faktörleri    :', json.load(open(OUT + 'monthly_factors_terra_v2.json')))
print('İki uydu faktörleri :', json.load(open(OUT + 'monthly_factors_v2.json')))

import glob
import numpy as np
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
RAW = '/content/drive/MyDrive/nasa_v2/raw/'

def load(source):
    frames = []
    for f in sorted(glob.glob(f'{RAW}{source}_*.csv')):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            pass
    return pd.concat(frames, ignore_index=True)

modis = load('MODIS_SP')
viirs = load('VIIRS_SNPP_SP')
modis['confidence'] = pd.to_numeric(modis['confidence'], errors='coerce')
modis = modis[(modis['confidence'] >= 30) & (modis['type'] == 0)].copy()
viirs = viirs[viirs['confidence'].astype(str).str.lower().isin(['n', 'h', 'nominal', 'high'])
              & (viirs['type'] == 0)].copy()
print('Temiz tespit sayısı:', len(modis), len(viirs), '(beklenen: 284313 590023)')

def prep(d):
    d = d.copy()
    dt = pd.to_datetime(d['acq_date'])
    d['year'] = dt.dt.year
    d['month'] = dt.dt.month
    return d[d['year'].between(2012, 2025)]

modis = prep(modis)
viirs = prep(viirs)
is_terra = modis['satellite'].astype(str).str.lower().str.startswith('t')

ym = ['year', 'month']
ov = pd.concat([viirs.groupby(ym).size().rename('V'),
                modis.groupby(ym).size().rename('M'),
                modis[is_terra].groupby(ym).size().rename('T')], axis=1).dropna().reset_index()

def rm(tr, num, den):
    g = tr.groupby('month')[[num, den]].sum()
    return g[num] / g[den]

def pred_a(tr, te):      # Terra verisi, Terra faktörü (şu an kullanılan)
    return te['T'] * te['month'].map(rm(tr, 'V', 'T'))

def pred_b(tr, te):      # Terra verisi, iki uydu faktörü
    return te['T'] * te['month'].map(rm(tr, 'V', 'M'))

def fixed():
    yield ov[ov['year'] <= 2018], ov[ov['year'] >= 2019]

def expanding():
    for y in range(2015, 2026):
        yield ov[ov['year'] < y], ov[ov['year'] == y]

def loyo():
    for y in range(2012, 2026):
        yield ov[ov['year'] != y], ov[ov['year'] == y]

def run(model, scheme):
    rs = []
    for i, (tr, te) in enumerate(scheme()):
        r = te[['year', 'month', 'V']].copy()
        r['P'] = np.asarray(model(tr, te))
        r['fold'] = i
        rs.append(r)
    return pd.concat(rs)

def wape(r):
    return (r['P'] - r['V']).abs().sum() / r['V'].sum() * 100

def bias(r):
    return (r['P'].sum() - r['V'].sum()) / r['V'].sum() * 100

schemes = (('Sabit', fixed), ('Ileriye genisleyen', expanding), ('Her yili disarida birak', loyo))
rows, cache = [], {}
for sname, scheme in schemes:
    for mname, m in (('a) Terra faktörü', pred_a), ('b) iki uydu faktörü', pred_b)):
        r = run(m, scheme)
        cache[(sname, mname[0])] = r
        rows.append({'sema': sname, 'model': mname, 'WAPE': wape(r), 'bias': bias(r)})
print('\nTerra-only veri, bölge aylık toplamı:')
print(pd.DataFrame(rows).round(1).to_string(index=False))

print('\nEşleştirilmiş WAPE farkı (a - b), yıllık katlar üzerinden:')
for sname, scheme in schemes:
    fa = cache[(sname, 'a')].groupby('fold').apply(wape)
    fb = cache[(sname, 'b')].groupby('fold').apply(wape)
    d = fa - fb
    se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float('nan')
    print(f'{sname:26s} | kat sayısı: {len(d):2d} | ort. fark: {d.mean():6.1f} | standart hata: {se:5.1f}')

import glob
import numpy as np
import pandas as pd
from google.colab import drive

drive.mount('/content/drive')
RAW = '/content/drive/MyDrive/nasa_v2/raw/'

def load(source):
    frames = []
    for f in sorted(glob.glob(f'{RAW}{source}_*.csv')):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            pass
    return pd.concat(frames, ignore_index=True)

modis = load('MODIS_SP')
viirs = load('VIIRS_SNPP_SP')
modis['confidence'] = pd.to_numeric(modis['confidence'], errors='coerce')
modis = modis[(modis['confidence'] >= 30) & (modis['type'] == 0)].copy()
viirs = viirs[viirs['confidence'].astype(str).str.lower().isin(['n', 'h', 'nominal', 'high'])
              & (viirs['type'] == 0)].copy()
print('Temiz tespit sayısı:', len(modis), len(viirs), '(beklenen: 284313 590023)')

def prep(d):
    d = d.copy()
    dt = pd.to_datetime(d['acq_date'])
    d['year'] = dt.dt.year
    d['month'] = dt.dt.month
    d['blok'] = (np.floor(d['latitude']).astype(int).astype(str) + '_' +
                 np.floor(d['longitude']).astype(int).astype(str))
    d['dn'] = d['daynight'].astype(str).str.upper().str[0]
    return d[d['year'].between(2012, 2025)]

modis = prep(modis)
viirs = prep(viirs)
print('daynight değerleri (MODIS, VIIRS):', sorted(modis['dn'].unique()), sorted(viirs['dn'].unique()))

# Blok x ay tablosu (sıfırlar dahil), gündüz ve gece ayrı
key = ['blok', 'year', 'month']
parts = {'V':  viirs.groupby(key).size(),
         'Vd': viirs[viirs['dn'] == 'D'].groupby(key).size(),
         'Vn': viirs[viirs['dn'] == 'N'].groupby(key).size(),
         'M':  modis.groupby(key).size(),
         'Md': modis[modis['dn'] == 'D'].groupby(key).size(),
         'Mn': modis[modis['dn'] == 'N'].groupby(key).size()}
tab = pd.concat(parts, axis=1).fillna(0).reset_index()
tot = tab.groupby(['year', 'month'])[['V', 'M']].sum()
ok = tot[(tot['V'] > 0) & (tot['M'] > 0)].reset_index()[['year', 'month']]
tam = pd.DataFrame({'blok': tab['blok'].unique()}).merge(ok, how='cross')
tab = tam.merge(tab, on=key, how='left').fillna(0)
print('Gündüz+gece toplamı ile toplam arasında fark olan satır sayısı:',
      int(((tab['Vd'] + tab['Vn'] != tab['V']) | (tab['Md'] + tab['Mn'] != tab['M'])).sum()))

# Tanı: gündüz ve gece faktörleri, gece payı (2012-2025)
ga = tab.groupby('month')[['V', 'Vd', 'Vn', 'M', 'Md', 'Mn']].sum()
diag = pd.DataFrame({'k_gunduz': ga['Vd'] / ga['Md'], 'k_gece': ga['Vn'] / ga['Mn'],
                     'k_toplam': ga['V'] / ga['M'],
                     'gece_payi_VIIRS_%': ga['Vn'] / ga['V'] * 100,
                     'gece_payi_MODIS_%': ga['Mn'] / ga['M'] * 100}).round(2)
print('\nAylık faktörler ve gece payları:')
print(diag)

def rm(tr, num, den):
    g = tr.groupby('month')[[num, den]].sum()
    return g[num] / g[den].replace(0, np.nan)

def pred_V0(tr, te):
    return te['M'] * te['month'].map(rm(tr, 'V', 'M'))

def pred_V2(tr, te):
    kd = rm(tr, 'Vd', 'Md')
    kn = rm(tr, 'Vn', 'Mn')
    return (te['Md'] * te['month'].map(kd)).fillna(0) + (te['Mn'] * te['month'].map(kn)).fillna(0)

models = {'V0 aylık faktör (mevcut)': pred_V0, 'V2 gündüz/gece ayrı faktör': pred_V2}

def fixed():
    yield tab[tab['year'] <= 2018], tab[tab['year'] >= 2019]

def expanding():
    for y in range(2015, 2026):
        yield tab[tab['year'] < y], tab[tab['year'] == y]

def loyo():
    for y in range(2012, 2026):
        yield tab[tab['year'] != y], tab[tab['year'] == y]

def run(model, scheme):
    rs = []
    for i, (tr, te) in enumerate(scheme()):
        r = te[['blok', 'year', 'month', 'V']].copy()
        r['P'] = np.asarray(model(tr, te))
        r['fold'] = i
        rs.append(r)
    return pd.concat(rs)

def wape(r):
    return (r['P'] - r['V']).abs().sum() / r['V'].sum() * 100

def bias(r):
    return (r['P'].sum() - r['V'].sum()) / r['V'].sum() * 100

def region(r):
    return r.groupby(['fold', 'year', 'month'])[['V', 'P']].sum().reset_index()

def fold_wape(r, level):
    out = {}
    for f, s in r.groupby('fold'):
        if level == 'bolge':
            s = s.groupby(['year', 'month'])[['V', 'P']].sum().reset_index()
        out[f] = wape(s)
    return pd.Series(out)

schemes = (('Sabit', fixed), ('Ileriye genisleyen', expanding), ('Her yili disarida birak', loyo))
cache, rows = {}, []
for sname, scheme in schemes:
    for mname, m in models.items():
        r = run(m, scheme)
        cache[(sname, mname)] = r
        rg = region(r)
        rows.append({'sema': sname, 'model': mname,
                     'bolge_WAPE': wape(rg), 'bolge_bias': bias(rg),
                     'blok_WAPE': wape(r), 'blok_bias': bias(r)})
print('\nModel karşılaştırması:')
print(pd.DataFrame(rows).round(1).to_string(index=False))

print('\nEşleştirilmiş WAPE farkı (V2 - V0), yıllık katlar üzerinden:')
for sname, scheme in schemes:
    for level in ('bolge', 'blok'):
        d = (fold_wape(cache[(sname, 'V2 gündüz/gece ayrı faktör')], level)
             - fold_wape(cache[(sname, 'V0 aylık faktör (mevcut)')], level))
        se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float('nan')
        print(f'{sname:26s} {level:6s} | kat sayısı: {len(d):2d} | ort. fark: {d.mean():6.1f} | standart hata: {se:5.1f}')

# FRP sınıfına göre dönüşüm faktörü testi (V3a, V3b) ve V0 ile karşılaştırma.
# Gece/gündüz hücresiyle aynı iskelet: blok x ay tablosu, üç şema, bölge ve blok WAPE/bias, eşleştirilmiş kat farkı.
# Sınır değerleri HER KATTA yalnızca o katın eğitim yıllarındaki MODIS FRP'sinden (%33 ve %67) yeniden hesaplanır (sızıntı yok).

import glob
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from google.colab import drive

drive.mount('/content/drive')
RAW = '/content/drive/MyDrive/nasa_v2/raw/'

def load(source):
    frames = []
    for f in sorted(glob.glob(f'{RAW}{source}_*.csv')):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            pass
    return pd.concat(frames, ignore_index=True)

modis = load('MODIS_SP')
viirs = load('VIIRS_SNPP_SP')
modis['confidence'] = pd.to_numeric(modis['confidence'], errors='coerce')
modis = modis[(modis['confidence'] >= 30) & (modis['type'] == 0)].copy()
viirs = viirs[viirs['confidence'].astype(str).str.lower().isin(['n', 'h', 'nominal', 'high'])
              & (viirs['type'] == 0)].copy()
print('Temiz tespit sayısı:', len(modis), len(viirs), '(beklenen: 284313 590023)')

def prep(d):
    d = d.copy()
    dt = pd.to_datetime(d['acq_date'])
    d['year'] = dt.dt.year
    d['month'] = dt.dt.month
    d['blok'] = (np.floor(d['latitude']).astype(int).astype(str) + '_' +
                 np.floor(d['longitude']).astype(int).astype(str))
    return d[d['year'].between(2012, 2025)]

modis = prep(modis)
viirs = prep(viirs)
modis = modis[modis['frp'].notna()].copy()   # FRP'siz MODIS satırı varsa sınıflanamaz

# Temel blok x ay tablosu (sıfırlar dahil), gece/gündüz hücresiyle aynı kural
key = ['blok', 'year', 'month']
base = pd.concat({'V': viirs.groupby(key).size(), 'M': modis.groupby(key).size()}, axis=1).fillna(0).reset_index()
tot = base.groupby(['year', 'month'])[['V', 'M']].sum()
ok = tot[(tot['V'] > 0) & (tot['M'] > 0)].reset_index()[['year', 'month']]
tam = pd.DataFrame({'blok': base['blok'].unique()}).merge(ok, how='cross')
base = tam.merge(base, on=key, how='left').fillna(0)
base['season'] = base['month'].map(lambda m: {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1,
                                              6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}[m])  # 0=DJF 1=MAM 2=JJA 3=SON

SINIF = ['M_dusuk', 'M_orta', 'M_yuksek']

# Katsayılar hangi satırlarla öğrenilsin?
#  'blok'  : blok x ay satırları (istemdeki gibi)
#  'bolge' : önce (yıl, ay) bazında bölge toplamına indirilir, sonra nnls (ortalamayı korur; blok düzeyindeki nnls küçük/seyrek karelerde katsayıyı aşağı çekebilir)
FIT = 'blok'
def fit_rows(tr):
    if FIT == 'bolge':
        return tr.groupby(['year', 'month', 'season'], as_index=False)[SINIF + ['V']].sum()
    return tr

def thresholds(train_years):
    fr = modis.loc[modis['year'].isin(train_years), 'frp']
    return np.quantile(fr, [0.33, 0.67])

_cache = {}
def build(train_years):
    """Bu katın eğitim yıllarından sınır hesapla, blok x ay x sınıf sayılarını tabloya ekle."""
    k = tuple(train_years)
    if k in _cache:
        return _cache[k]
    q1, q2 = thresholds(train_years)
    cls = np.where(modis['frp'] < q1, 0, np.where(modis['frp'] < q2, 1, 2))   # düşük < q33 <= orta < q67 <= yüksek
    c = (modis.assign(sinif=cls).groupby(key + ['sinif']).size().unstack(fill_value=0)
              .reindex(columns=[0, 1, 2], fill_value=0))
    c.columns = SINIF
    T = base.merge(c.reset_index(), on=key, how='left')
    T[SINIF] = T[SINIF].fillna(0)
    _cache[k] = (T, q1, q2)
    return _cache[k]

# --- Modeller ---
def rm(tr, num, den):
    g = tr.groupby('month')[[num, den]].sum()
    return g[num] / g[den].replace(0, np.nan)

def pred_V0(tr, te):
    return te['M'] * te['month'].map(rm(tr, 'V', 'M')), None

def fit_a(tr):
    tr = fit_rows(tr)
    coef, _ = nnls(tr[SINIF].to_numpy(float), tr['V'].to_numpy(float))
    return coef

def pred_V3a(tr, te):
    coef = fit_a(tr)
    return te[SINIF].to_numpy(float) @ coef, coef

def design_b(d):
    X = np.zeros((len(d), 12))
    S = d['season'].to_numpy()
    M = d[SINIF].to_numpy(float)
    for s in range(4):
        m = S == s
        X[m, s * 3:(s + 1) * 3] = M[m]
    return X

def fit_b(tr):
    tr = fit_rows(tr)
    coef, _ = nnls(design_b(tr), tr['V'].to_numpy(float))
    return coef

def pred_V3b(tr, te):
    coef = fit_b(tr)
    return design_b(te) @ coef, coef

models = {'V0 aylık faktör (mevcut)': pred_V0,
          'V3a FRP sınıfı (3 katsayı)': pred_V3a,
          'V3b FRP sınıfı x mevsim (12 katsayı)': pred_V3b}

# --- Şemalar: (eğitim yılları, test yılları) ---
Y = list(range(2012, 2026))
def fixed():
    yield [y for y in Y if y <= 2018], [y for y in Y if y >= 2019]
def expanding():
    for y in range(2015, 2026):
        yield [t for t in Y if t < y], [y]
def loyo():
    for y in Y:
        yield [t for t in Y if t != y], [y]

coef_log = {}
def run(mname, model, sname, scheme):
    rs = []
    for i, (tr_y, te_y) in enumerate(scheme()):
        T, _, _ = build(tr_y)
        tr, te = T[T['year'].isin(tr_y)], T[T['year'].isin(te_y)]
        r = te[['blok', 'year', 'month', 'V']].copy()
        p, coef = model(tr, te)
        r['P'] = np.asarray(p)
        r['fold'] = i
        if coef is not None:
            coef_log.setdefault((sname, mname), []).append(coef)
        rs.append(r)
    return pd.concat(rs)

def wape(r):
    return (r['P'] - r['V']).abs().sum() / r['V'].sum() * 100

def bias(r):
    return (r['P'].sum() - r['V'].sum()) / r['V'].sum() * 100

def region(r):
    return r.groupby(['fold', 'year', 'month'])[['V', 'P']].sum().reset_index()

def fold_wape(r, level):
    out = {}
    for f, s in r.groupby('fold'):
        if level == 'bolge':
            s = s.groupby(['year', 'month'])[['V', 'P']].sum().reset_index()
        out[f] = wape(s)
    return pd.Series(out)

schemes = (('Sabit', fixed), ('Ileriye genisleyen', expanding), ('Her yili disarida birak', loyo))
cache, rows = {}, []
for sname, scheme in schemes:
    for mname, m in models.items():
        r = run(mname, m, sname, scheme)
        cache[(sname, mname)] = r
        rg = region(r)
        rows.append({'sema': sname, 'model': mname, 'bolge_WAPE': wape(rg), 'bolge_bias': bias(rg),
                     'blok_WAPE': wape(r), 'blok_bias': bias(r)})
res = pd.DataFrame(rows).round(1)
print('\nDoğrulama: Sabit şemada V0 için bölge WAPE 17,9, bias +7,6, blok WAPE 47,1 çıkmalı (çıkmazsa sonuçlara güvenme).')
print('\nModel karşılaştırması:')
print(res.to_string(index=False))

print('\nEşleştirilmiş WAPE farkı (model - V0), yıllık katlar üzerinden (pozitif = V0 daha iyi):')
V0 = 'V0 aylık faktör (mevcut)'
for mname in list(models)[1:]:
    print(mname)
    for sname, scheme in schemes:
        for level in ('bolge', 'blok'):
            d = fold_wape(cache[(sname, mname)], level) - fold_wape(cache[(sname, V0)], level)
            se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float('nan')
            print(f'  {sname:26s} {level:6s} | kat sayısı: {len(d):2d} | ort. fark: {d.mean():6.1f} | standart hata: {se:5.1f}')

# --- Tanı 1: sınıf sınırları (MW) ve sınıf payları (sabit şemanın eğitim yıllarındaki sınırlarla, 2012-2025 tüm MODIS) ---
T, q1, q2 = build([y for y in Y if y <= 2018])
print(f'\nSınıf sınırları (2012-2018 MODIS FRP): düşük < {q1:.2f} MW <= orta < {q2:.2f} MW <= yüksek')
cls = np.where(modis['frp'] < q1, 'dusuk', np.where(modis['frp'] < q2, 'orta', 'yuksek'))
pay = (pd.crosstab(modis['month'], cls, normalize='index') * 100).round(1)[['dusuk', 'orta', 'yuksek']]
print('\nMODIS tespitlerinde FRP sınıfı payı (%), ay ay (2012-2025):')
print(pay)
print('\nHer katta hesaplanan sınırların aralığı (MW): q33',
      '%.2f-%.2f' % (min(build(a)[1] for a, _ in loyo()), max(build(a)[1] for a, _ in loyo())),
      '| q67', '%.2f-%.2f' % (min(build(a)[2] for a, _ in loyo()), max(build(a)[2] for a, _ in loyo())))

# --- Tanı 2: katsayılar (sabit şemanın eğitimi 2012-2018) ---
tr = T[T['year'] <= 2018]
ka = fit_a(tr)
print('\nV3a katsayıları (k1 düşük, k2 orta, k3 yüksek):', dict(zip(['k1', 'k2', 'k3'], ka.round(2))))
print('k1 > k2 > k3 mi?', bool(ka[0] > ka[1] > ka[2]))
kb = fit_b(tr).reshape(4, 3)
tb = pd.DataFrame(kb, index=['DJF', 'MAM', 'JJA', 'SON'], columns=['k1_dusuk', 'k2_orta', 'k3_yuksek']).round(2)
tb['k1>k2>k3'] = (tb['k1_dusuk'] > tb['k2_orta']) & (tb['k2_orta'] > tb['k3_yuksek'])
print('\nV3b katsayıları (mevsim x sınıf):')
print(tb)

# Katsayıların kat bazında kararlılığı (her yılı dışarıda bırak)
L = np.array(coef_log[('Her yili disarida birak', 'V3a FRP sınıfı (3 katsayı)')])
print('\nV3a katsayı aralığı, her yılı dışarıda bırak (min-max):',
      {f'k{i+1}': f'{L[:, i].min():.2f}-{L[:, i].max():.2f}' for i in range(3)})
print('Sıralama k1>k2>k3 olan kat sayısı:', int(((L[:, 0] > L[:, 1]) & (L[:, 1] > L[:, 2])).sum()), '/', len(L))

# FRP sınıfına göre dönüşüm faktörü testi (V3a, V3b) ve V0 ile karşılaştırma.
# Gece/gündüz hücresiyle aynı iskelet: blok x ay tablosu, üç şema, bölge ve blok WAPE/bias, eşleştirilmiş kat farkı.
# Sınır değerleri HER KATTA yalnızca o katın eğitim yıllarındaki MODIS FRP'sinden (%33 ve %67) yeniden hesaplanır (sızıntı yok).

import glob
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from google.colab import drive

drive.mount('/content/drive')
RAW = '/content/drive/MyDrive/nasa_v2/raw/'

def load(source):
    frames = []
    for f in sorted(glob.glob(f'{RAW}{source}_*.csv')):
        try:
            frames.append(pd.read_csv(f))
        except pd.errors.EmptyDataError:
            pass
    return pd.concat(frames, ignore_index=True)

modis = load('MODIS_SP')
viirs = load('VIIRS_SNPP_SP')
modis['confidence'] = pd.to_numeric(modis['confidence'], errors='coerce')
modis = modis[(modis['confidence'] >= 30) & (modis['type'] == 0)].copy()
viirs = viirs[viirs['confidence'].astype(str).str.lower().isin(['n', 'h', 'nominal', 'high'])
              & (viirs['type'] == 0)].copy()
print('Temiz tespit sayısı:', len(modis), len(viirs), '(beklenen: 284313 590023)')

def prep(d):
    d = d.copy()
    dt = pd.to_datetime(d['acq_date'])
    d['year'] = dt.dt.year
    d['month'] = dt.dt.month
    d['blok'] = (np.floor(d['latitude']).astype(int).astype(str) + '_' +
                 np.floor(d['longitude']).astype(int).astype(str))
    return d[d['year'].between(2012, 2025)]

modis = prep(modis)
viirs = prep(viirs)
modis = modis[modis['frp'].notna()].copy()   # FRP'siz MODIS satırı varsa sınıflanamaz

# Temel blok x ay tablosu (sıfırlar dahil), gece/gündüz hücresiyle aynı kural
key = ['blok', 'year', 'month']
base = pd.concat({'V': viirs.groupby(key).size(), 'M': modis.groupby(key).size()}, axis=1).fillna(0).reset_index()
tot = base.groupby(['year', 'month'])[['V', 'M']].sum()
ok = tot[(tot['V'] > 0) & (tot['M'] > 0)].reset_index()[['year', 'month']]
tam = pd.DataFrame({'blok': base['blok'].unique()}).merge(ok, how='cross')
base = tam.merge(base, on=key, how='left').fillna(0)
base['season'] = base['month'].map(lambda m: {12: 0, 1: 0, 2: 0, 3: 1, 4: 1, 5: 1,
                                              6: 2, 7: 2, 8: 2, 9: 3, 10: 3, 11: 3}[m])  # 0=DJF 1=MAM 2=JJA 3=SON

SINIF = ['M_dusuk', 'M_orta', 'M_yuksek']

# Katsayılar hangi satırlarla öğrenilsin?
#  'blok'  : blok x ay satırları (istemdeki gibi)
#  'bolge' : önce (yıl, ay) bazında bölge toplamına indirilir, sonra nnls (ortalamayı korur; blok düzeyindeki nnls küçük/seyrek karelerde katsayıyı aşağı çekebilir)
FIT = 'blok'   # aşağıdaki döngü bunu otomatik olarak 'blok' ve 'bolge' yapar, elle değiştirme
def fit_rows(tr):
    if FIT == 'bolge':
        return tr.groupby(['year', 'month', 'season'], as_index=False)[SINIF + ['V']].sum()
    return tr

def thresholds(train_years):
    fr = modis.loc[modis['year'].isin(train_years), 'frp']
    return np.quantile(fr, [0.33, 0.67])

_cache = {}
def build(train_years):
    """Bu katın eğitim yıllarından sınır hesapla, blok x ay x sınıf sayılarını tabloya ekle."""
    k = tuple(train_years)
    if k in _cache:
        return _cache[k]
    q1, q2 = thresholds(train_years)
    cls = np.where(modis['frp'] < q1, 0, np.where(modis['frp'] < q2, 1, 2))   # düşük < q33 <= orta < q67 <= yüksek
    c = (modis.assign(sinif=cls).groupby(key + ['sinif']).size().unstack(fill_value=0)
              .reindex(columns=[0, 1, 2], fill_value=0))
    c.columns = SINIF
    T = base.merge(c.reset_index(), on=key, how='left')
    T[SINIF] = T[SINIF].fillna(0)
    _cache[k] = (T, q1, q2)
    return _cache[k]

# --- Modeller ---
def rm(tr, num, den):
    g = tr.groupby('month')[[num, den]].sum()
    return g[num] / g[den].replace(0, np.nan)

def pred_V0(tr, te):
    return te['M'] * te['month'].map(rm(tr, 'V', 'M')), None

def fit_a(tr):
    tr = fit_rows(tr)
    coef, _ = nnls(tr[SINIF].to_numpy(float), tr['V'].to_numpy(float))
    return coef

def pred_V3a(tr, te):
    coef = fit_a(tr)
    return te[SINIF].to_numpy(float) @ coef, coef

def design_b(d):
    X = np.zeros((len(d), 12))
    S = d['season'].to_numpy()
    M = d[SINIF].to_numpy(float)
    for s in range(4):
        m = S == s
        X[m, s * 3:(s + 1) * 3] = M[m]
    return X

def fit_b(tr):
    tr = fit_rows(tr)
    coef, _ = nnls(design_b(tr), tr['V'].to_numpy(float))
    return coef

def pred_V3b(tr, te):
    coef = fit_b(tr)
    return design_b(te) @ coef, coef

models = {'V0 aylık faktör (mevcut)': pred_V0,
          'V3a FRP sınıfı (3 katsayı)': pred_V3a,
          'V3b FRP sınıfı x mevsim (12 katsayı)': pred_V3b}

# --- Şemalar: (eğitim yılları, test yılları) ---
Y = list(range(2012, 2026))
def fixed():
    yield [y for y in Y if y <= 2018], [y for y in Y if y >= 2019]
def expanding():
    for y in range(2015, 2026):
        yield [t for t in Y if t < y], [y]
def loyo():
    for y in Y:
        yield [t for t in Y if t != y], [y]

coef_log = {}
def run(mname, model, sname, scheme):
    rs = []
    for i, (tr_y, te_y) in enumerate(scheme()):
        T, _, _ = build(tr_y)
        tr, te = T[T['year'].isin(tr_y)], T[T['year'].isin(te_y)]
        r = te[['blok', 'year', 'month', 'V']].copy()
        p, coef = model(tr, te)
        r['P'] = np.asarray(p)
        r['fold'] = i
        if coef is not None:
            coef_log.setdefault((sname, mname), []).append(coef)
        rs.append(r)
    return pd.concat(rs)

def wape(r):
    return (r['P'] - r['V']).abs().sum() / r['V'].sum() * 100

def bias(r):
    return (r['P'].sum() - r['V'].sum()) / r['V'].sum() * 100

def region(r):
    return r.groupby(['fold', 'year', 'month'])[['V', 'P']].sum().reset_index()

def fold_wape(r, level):
    out = {}
    for f, s in r.groupby('fold'):
        if level == 'bolge':
            s = s.groupby(['year', 'month'])[['V', 'P']].sum().reset_index()
        out[f] = wape(s)
    return pd.Series(out)

# --- Tanı 1: sınıf sınırları (MW) ve sınıf payları (sabit şemanın eğitim yıllarındaki sınırlarla, 2012-2025 tüm MODIS) ---
T, q1, q2 = build([y for y in Y if y <= 2018])
print(f'\nSınıf sınırları (2012-2018 MODIS FRP): düşük < {q1:.2f} MW <= orta < {q2:.2f} MW <= yüksek')
cls = np.where(modis['frp'] < q1, 'dusuk', np.where(modis['frp'] < q2, 'orta', 'yuksek'))
pay = (pd.crosstab(modis['month'], cls, normalize='index') * 100).round(1)[['dusuk', 'orta', 'yuksek']]
print('\nMODIS tespitlerinde FRP sınıfı payı (%), ay ay (2012-2025):')
print(pay)
print('\nHer katta hesaplanan sınırların aralığı (MW): q33',
      '%.2f-%.2f' % (min(build(a)[1] for a, _ in loyo()), max(build(a)[1] for a, _ in loyo())),
      '| q67', '%.2f-%.2f' % (min(build(a)[2] for a, _ in loyo()), max(build(a)[2] for a, _ in loyo())))


for FIT in ('blok', 'bolge'):
    coef_log.clear()
    print('\n' + '=' * 70)
    print('KATSAYILAR', 'BLOK x AY satırlarıyla (istemdeki gibi)' if FIT == 'blok' else 'BÖLGE-AY toplamlarıyla', 'öğrenildi  [FIT =', FIT + ']')
    print('=' * 70)
    schemes = (('Sabit', fixed), ('Ileriye genisleyen', expanding), ('Her yili disarida birak', loyo))
    cache, rows = {}, []
    for sname, scheme in schemes:
        for mname, m in models.items():
            r = run(mname, m, sname, scheme)
            cache[(sname, mname)] = r
            rg = region(r)
            rows.append({'sema': sname, 'model': mname, 'bolge_WAPE': wape(rg), 'bolge_bias': bias(rg),
                         'blok_WAPE': wape(r), 'blok_bias': bias(r)})
    res = pd.DataFrame(rows).round(1)
    print('\nDoğrulama: Sabit şemada V0 için bölge WAPE 17,9, bias +7,6, blok WAPE 47,1 çıkmalı (çıkmazsa sonuçlara güvenme).')
    print('\nModel karşılaştırması:')
    print(res.to_string(index=False))

    print('\nEşleştirilmiş WAPE farkı (model - V0), yıllık katlar üzerinden (pozitif = V0 daha iyi):')
    V0 = 'V0 aylık faktör (mevcut)'
    for mname in list(models)[1:]:
        print(mname)
        for sname, scheme in schemes:
            for level in ('bolge', 'blok'):
                d = fold_wape(cache[(sname, mname)], level) - fold_wape(cache[(sname, V0)], level)
                se = d.std(ddof=1) / np.sqrt(len(d)) if len(d) > 1 else float('nan')
                print(f'  {sname:26s} {level:6s} | kat sayısı: {len(d):2d} | ort. fark: {d.mean():6.1f} | standart hata: {se:5.1f}')

    # --- Tanı 2: katsayılar (sabit şemanın eğitimi 2012-2018) ---
    tr = T[T['year'] <= 2018]
    ka = fit_a(tr)
    print('\nV3a katsayıları (k1 düşük, k2 orta, k3 yüksek):', dict(zip(['k1', 'k2', 'k3'], ka.round(2))))
    print('k1 > k2 > k3 mi?', bool(ka[0] > ka[1] > ka[2]))
    kb = fit_b(tr).reshape(4, 3)
    tb = pd.DataFrame(kb, index=['DJF', 'MAM', 'JJA', 'SON'], columns=['k1_dusuk', 'k2_orta', 'k3_yuksek']).round(2)
    tb['k1>k2>k3'] = (tb['k1_dusuk'] > tb['k2_orta']) & (tb['k2_orta'] > tb['k3_yuksek'])
    print('\nV3b katsayıları (mevsim x sınıf):')
    print(tb)

    # Katsayıların kat bazında kararlılığı (her yılı dışarıda bırak)
    L = np.array(coef_log[('Her yili disarida birak', 'V3a FRP sınıfı (3 katsayı)')])
    print('\nV3a katsayı aralığı, her yılı dışarıda bırak (min-max):',
          {f'k{i+1}': f'{L[:, i].min():.2f}-{L[:, i].max():.2f}' for i in range(3)})
    print('Sıralama k1>k2>k3 olan kat sayısı:', int(((L[:, 0] > L[:, 1]) & (L[:, 1] > L[:, 2])).sum()), '/', len(L))