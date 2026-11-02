// p02 · Valida el motor en JavaScript contra el motor en Python (referencia de p01).
// Uso: node 02_SCRIPTS/productos/p02_validar_motor_js.js
// Los azares son distintos (otra semilla, otro generador): se espera acuerdo dentro del error de
// Monte Carlo, no igualdad. Con 1.000 simulaciones, P(gana) tiene un error de ±0,03.
const fs = require("fs");
const path = require("path");
const M = require("./motor_2027.js");

const dir = path.join(__dirname, "..", "..", "03_OUTPUTS", "simulador");
const D = JSON.parse(fs.readFileSync(path.join(dir, "datos_simulador.json"), "utf8"));
const ref = JSON.parse(fs.readFileSync(path.join(dir, "referencia_python.json"), "utf8"));
const P = M.preparar(D);
const med = (a) => M.percentil(a, 50);
let ok = true;
const filas = [];
for (const r of ref) {
  const k = r.parametros;
  const o = { base: k.base, part: k.part ?? 0.76, n: 1000, semilla: 7,
              metas: k.metas ? D.bloques.map((b) => k.metas[b]) : null,
              piProv: k.pi_prov ?? null, sdPi: k.sd_pi_provincial ?? 0 };
  const t0 = Date.now();
  const s = M.simular(P, o);
  const per = s.nombres.indexOf("PERONISMO");
  const js = {
    p: s.pGana, margen: med(s.margen), munis: med(s.munisPrimero),
    dip: med(s.dip.map((d) => d[per])), sen: med(s.sen.map((d) => d[per])),
    pct: s.nombres.map((_, k) => s.R.reduce((a, x) => a + x[k], 0) / s.n),
    sec: s.secIds.map((_, k) => s.secPrimero[k * s.nombres.length + per]),
  };
  const py = { p: r.p_gana_peronismo, margen: r.margen_p10_p50_p90[1], munis: r.municipios_peronismo_p50,
               dip: r.diputados_2027_peronismo_p50, sen: r.senadores_2027_peronismo_p50,
               pct: s.nombres.map((n) => r.pct[n]), sec: s.secIds.map((x) => r.secciones_p_peronismo[x]) };
  const dPct = Math.max(...js.pct.map((v, i) => Math.abs(v - py.pct[i])));
  const dSec = Math.max(...js.sec.map((v, i) => Math.abs(v - py.sec[i])));
  const pasa = Math.abs(js.p - py.p) <= 0.05 && Math.abs(js.margen - py.margen) <= 0.3 && dPct <= 0.3 &&
               Math.abs(js.munis - py.munis) <= 2 && Math.abs(js.dip - py.dip) <= 1 && Math.abs(js.sen - py.sen) <= 1 && dSec <= 0.06;
  ok = ok && pasa;
  filas.push({ caso: r.caso, P_py: py.p, P_js: +js.p.toFixed(3), margen_py: py.margen, margen_js: +js.margen.toFixed(2),
               munis: `${py.munis}/${js.munis}`, dip: `${py.dip}/${js.dip}`, sen: `${py.sen}/${js.sen}`,
               max_dif_pct: +dPct.toFixed(2), max_dif_seccion: +dSec.toFixed(3), seg: (Date.now() - t0) / 1000, pasa });
}
console.table(filas);
fs.writeFileSync(path.join(dir, "validacion_motor_js.json"), JSON.stringify(filas, null, 1));
console.log(ok ? "OK: el motor JS reproduce al de Python" : "DIFERENCIAS: revisar");
process.exit(ok ? 0 : 1);
