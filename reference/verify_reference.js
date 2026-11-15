// node reference/verify_reference.js  -> runs the team's analyze() on ../daily_grid_v2.csv
// AI/SI disclosure: this script was written with the help of AI tools (Claude, Gemini); the analyze() function it runs is the team's reference (reference/JS_fonksiyonu.txt).
const fs=require('fs');
const analyze=new Function(fs.readFileSync(__dirname+'/JS_fonksiyonu.txt','utf8')+';return analyze;')();
function checkFile(csvFile, outJson){
  const ln=fs.readFileSync(__dirname+'/../'+csvFile,'utf8').trim().split('\n').slice(1);
  const rows=ln.map(s=>{const c=s.split(',');return{date:c[0],intensity:+c[4]}});
  const run=(z,mi)=>{const r=analyze(rows,2003,2025,z,mi);return{params:{y0:2003,y1:2025,zThr:z,minInt:mi},critical_js_index:r.critical,core_js_index:r.core,critical_week_1based:r.critical.map(w=>w+1),core_week_1based:r.core.map(w=>w+1),anomaly_count:r.anomalies.length,anomalies:r.anomalies.map(a=>({year:a.year,week_js:a.week,week_1based:a.week+1,intensity:Math.round(a.intensity*10)/10,z:Math.round(a.z*100)/100}))}};
  const out={default_minInt20:run(2,20),minInt5:run(2,5)};
  fs.writeFileSync(__dirname+'/'+outJson,JSON.stringify(out,null,1));
  console.log('=== '+csvFile+' ===');
  for(const k in out)console.log(k,'critical (1-based):',out[k].critical_week_1based.join(','),'| (0-based):',out[k].critical_js_index.join(','),'| core (1-based):',out[k].core_week_1based.join(','),'| (0-based):',out[k].core_js_index.join(','),'| anomalies:',out[k].anomaly_count);
}
checkFile('daily_grid_v2.csv','validation_values_v2.json');
