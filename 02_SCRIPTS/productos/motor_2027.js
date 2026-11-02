/*
 * Motor 2027 en JavaScript: traducción de `analisis/106_motor_2027.py` (Motor.simular) y del reparto
 * de bancas de `analisis/108_legislatura_2027.py`. Corre en el navegador (simulador) y en Node
 * (validación contra el motor en Python: `node p02_validar_motor_js.js`).
 *
 * Unidades: los repartos son fracciones de los votos positivos (suman 1); `metas` va en %.
 */
(function (raiz) {
  "use strict";

  // ------------------------------------------------------------------ azar con semilla
  function rng(semilla) {
    let a = (semilla >>> 0) || 1;
    const u = () => {
      a = (a + 0x6d2b79f5) >>> 0;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
    let guardado = null;
    const normal = () => {
      if (guardado !== null) { const g = guardado; guardado = null; return g; }
      let x = 0, y = 0;
      while (x === 0) x = u();
      y = u();
      const r = Math.sqrt(-2 * Math.log(x));
      guardado = r * Math.sin(2 * Math.PI * y);
      return r * Math.cos(2 * Math.PI * y);
    };
    // t de `gl` grados (entero) escalada a varianza 1, como en el motor.
    const t = (gl) => {
      let chi = 0;
      for (let i = 0; i < gl; i++) { const z = normal(); chi += z * z; }
      return normal() / Math.sqrt(chi / gl) * Math.sqrt((gl - 2) / gl);
    };
    return { u, normal, t };
  }

  // ------------------------------------------------------------------ reparto territorial (105)
  function agregado(s, w, n, K) {
    const out = new Float64Array(K);
    let W = 0;
    for (let i = 0; i < n; i++) {
      W += w[i];
      for (let k = 0; k < K; k++) out[k] += s[i * K + k] * w[i];
    }
    for (let k = 0; k < K; k++) out[k] /= W;
    return out;
  }

  // s1 ∝ s0·exp(δ), con δ tal que el agregado dé S1. Corta cuando converge (tolerancia 1e-9).
  function proporcional(s0in, w, S1, n, K, iters = 200) {
    const s0 = Float64Array.from(s0in);
    const A0 = agregado(s0, w, n, K);
    const nuevo = Array.from(A0, (v) => v < 1e-4);
    if (nuevo.some(Boolean)) {
      for (let i = 0; i < n; i++) {
        let t = 0;
        for (let k = 0; k < K; k++) { if (nuevo[k]) s0[i * K + k] = 1e-3; t += s0[i * K + k]; }
        for (let k = 0; k < K; k++) s0[i * K + k] /= t;
      }
    }
    const delta = new Float64Array(K);
    const s1 = new Float64Array(n * K);
    const calc = () => {
      const e = Array.from(delta, Math.exp);
      for (let i = 0; i < n; i++) {
        let t = 0;
        for (let k = 0; k < K; k++) { const v = s0[i * K + k] * e[k]; s1[i * K + k] = v; t += v; }
        for (let k = 0; k < K; k++) s1[i * K + k] /= t;
      }
    };
    for (let it = 0; it < iters; it++) {
      calc();
      const agg = agregado(s1, w, n, K);
      let maxd = 0;
      for (let k = 0; k < K; k++) {
        if (S1[k] === 0) { delta[k] = -50; continue; }
        if (S1[k] > 0 && agg[k] > 0) {
          const d = Math.log(S1[k] / agg[k]);
          delta[k] += d;
          maxd = Math.max(maxd, Math.abs(d));
        }
      }
      if (maxd < 1e-9) break;
    }
    calc();
    return s1;
  }

  function uniforme(s0, w, S1, n, K) {
    const S0 = agregado(s0, w, n, K);
    const s1 = new Float64Array(n * K);
    for (let i = 0; i < n; i++) {
      let t = 0;
      for (let k = 0; k < K; k++) { const v = Math.max(s0[i * K + k] + S1[k] - S0[k], 0); s1[i * K + k] = v; t += v; }
      if (t > 0) for (let k = 0; k < K; k++) s1[i * K + k] /= t;
    }
    return s1;
  }

  function mezcla(s0, w, S1, n, K, peso = 0.5) {
    const p = proporcional(s0, w, S1, n, K), u = uniforme(s0, w, S1, n, K);
    const out = new Float64Array(n * K);
    for (let j = 0; j < n * K; j++) out[j] = peso * p[j] + (1 - peso) * u[j];
    return out;
  }

  // Participación provincial `meta` escalando el odds de cada circuito (bisección).
  function escalarParticipacion(pBase, el, meta) {
    const n = pBase.length, odds = new Float64Array(n);
    let E = 0;
    for (let i = 0; i < n; i++) { const p = Math.min(Math.max(pBase[i], 0.05), 0.97); odds[i] = p / (1 - p); E += el[i]; }
    let lo = 0.05, hi = 20, k = 1;
    for (let it = 0; it < 60; it++) {
      k = (lo + hi) / 2;
      let s = 0;
      for (let i = 0; i < n; i++) s += el[i] * k * odds[i] / (1 + k * odds[i]);
      if (s / E < meta) lo = k; else hi = k;
    }
    return Float64Array.from(odds, (o) => k * o / (1 + k * o));
  }

  // ------------------------------------------------------------------ bancas (108)
  // Ley 5.109, arts. 115-116: cociente, sin representación bajo el cociente, residuos.
  function reparto(votos, bancas, elegibles) {
    const nombres = Object.keys(votos);
    const total = nombres.reduce((a, k) => a + votos[k], 0);
    if (total <= 0) return {};
    const cand = nombres.filter((k) => !elegibles || elegibles.has(k));
    const q = total / bancas;
    const piso = cand.some((k) => votos[k] >= q) ? q : q / 2;
    const pasan = cand.filter((k) => votos[k] >= piso);
    const asign = {};
    pasan.forEach((k) => { asign[k] = Math.floor(votos[k] / q); });
    let faltan = bancas - pasan.reduce((a, k) => a + asign[k], 0);
    const orden = [...pasan].sort((a, b) => {
      const ra = votos[a] / q - Math.floor(votos[a] / q), rb = votos[b] / q - Math.floor(votos[b] / q);
      return rb - ra || votos[b] - votos[a];
    });
    orden.slice(0, Math.max(faltan, 0)).forEach((k) => { asign[k] += 1; });
    faltan = bancas - pasan.reduce((a, k) => a + asign[k], 0);
    if (faltan > 0 && pasan.length) {
      const mas = pasan.reduce((a, b) => (votos[b] > votos[a] ? b : a));
      asign[mas] += faltan;
    }
    return asign;
  }

  // ------------------------------------------------------------------ preparación
  function preparar(D) {
    const C = D.circuitos, n = C.w.length, K = D.bloques.length, M = D.municipios.length;
    const plano = (m) => Float64Array.from(m.flat());
    const P = {
      D, n, K, M,
      muni: Int32Array.from(C.muni), w: Float64Array.from(C.w),
      s: { octubre: plano(C.s_oct), septiembre: plano(C.s_sep) },
      el27: Float64Array.from(C.el27), p23: Float64Array.from(C.p23), p25: Float64Array.from(C.p25),
      pi23: Float64Array.from(C.pi23),
    };
    const secIds = [...new Set(D.municipios.map((m) => m.seccion))].sort();
    P.secIds = secIds;
    P.secDeMuni = Int32Array.from(D.municipios, (m) => secIds.indexOf(m.seccion));
    P.wM = new Float64Array(M);
    for (let i = 0; i < n; i++) P.wM[P.muni[i]] += P.w[i];
    // Extranjeros: padrón, reparto y participación de 2023 por municipio.
    const ok = D.municipios.filter((m) => m.ext_part !== null && m.ext_part === m.ext_part);
    P.extPartMedia = ok.reduce((a, m) => a + m.ext_part, 0) / Math.max(ok.length, 1);
    return P;
  }

  // ------------------------------------------------------------------ simulación (106)
  function simular(P, o) {
    const { D, n, K, M, muni, w, secIds, secDeMuni, wM } = P;
    const R = rng(o.semilla || 1);
    const base = o.base || "octubre";
    const s0 = P.s[base];
    let sEsc = s0;
    if (o.metas) {
      const tot = o.metas.reduce((a, b) => a + b, 0);
      sEsc = mezcla(s0, w, o.metas.map((v) => v / tot), n, K);
    }
    const SEsc = agregado(sEsc, w, n, K);
    const ruido = D.ruido[o.regimen || "oferta estable"];
    const gl = ruido.gl_t;
    const GL = D.gl;
    const dividida = o.piProv !== null && o.piProv !== undefined;
    const nombres = dividida ? ["PERONISMO", "LLA", "PRO", "TERCERA", "IZQUIERDA", "RESTO"] : D.bloques.slice();
    const KK = nombres.length;
    const nSim = o.n || 1000;
    const sdProv = o.sdProvincial === undefined ? 0.02 : o.sdProvincial;

    const q = escalarParticipacion(P.p23, P.el27, o.part === undefined ? 0.76 : o.part);
    const votantes = Float64Array.from(q, (v, i) => P.el27[i] * v * 0.95);
    // Movilización diferencial (109): opcional.
    let vBase = null, dV = null, perfil = null;
    if (o.perfilMarginal) {
      const qb = escalarParticipacion(P.p25, P.el27, o.partBase);
      const qn = escalarParticipacion(P.p25, P.el27, o.part);
      vBase = Float64Array.from(qb, (v, i) => P.el27[i] * v * 0.95);
      dV = Float64Array.from(qn, (v, i) => P.el27[i] * (v - qb[i]));
      perfil = D.bloques.map((b) => o.perfilMarginal[b] || 0);
    }
    // Voto extranjero por municipio (5 bloques).
    const ext = new Float64Array(M * K);
    D.municipios.forEach((m, j) => {
      if (!m.ext_rep || !m.ext_el) return;
      const pe = o.partExt === null || o.partExt === undefined ? (m.ext_part ?? P.extPartMedia) : o.partExt;
      for (let k = 0; k < K; k++) ext[j * K + k] = m.ext_rep[k] * m.ext_el * pe * 0.95;
    });
    const sigM = Float64Array.from(wM, (v) => ruido.escala * Math.exp(ruido.a + ruido.b * Math.log(v)));
    const cSec = Float64Array.from(sigM, (s) => Math.min(ruido.sd_seccion, Math.sqrt(0.8) * s));
    const sigPropio = Float64Array.from(sigM, (s, j) => Math.sqrt(Math.max(s * s - cSec[j] * cSec[j], 0)));
    const RP = D.ruido_pi;
    const sigPi = Float64Array.from(wM, (v) => RP.escala * Math.exp(RP.a + RP.b * Math.log(v)));
    const lg = Float64Array.from(P.pi23, (p) => Math.log(p / (1 - p)));
    const nS = secIds.length;
    const L = D.legislatura;
    const elegibles = new Set(nombres.filter((x) => x !== "RESTO"));

    const out = {
      nombres, secIds, n: nSim, R: [], margen: [], munisPrimero: [], dip: [], sen: [],
      muniPrimero: new Float64Array(M * KK), muniSh: new Float64Array(M * KK),
      secPrimero: new Float64Array(nS * KK), secSh: new Float64Array(nS * KK), secBancas: new Float64Array(nS * KK),
      SEsc: Array.from(SEsc, (v) => v * 100),
    };
    const e = new Float64Array(M), uS = new Float64Array(nS);
    for (let it = 0; it < nSim; it++) {
      const d = R.t(GL) * sdProv;
      let S = Float64Array.from(SEsc);
      S[0] += d / 2; S[1] -= d / 2;
      let tS = 0;
      for (let k = 0; k < K; k++) { S[k] = Math.max(S[k], 1e-4); tS += S[k]; }
      for (let k = 0; k < K; k++) S[k] /= tS;
      const s = sdProv > 0 ? mezcla(sEsc, w, S, n, K) : Float64Array.from(sEsc);
      // Ruido: shock de sección + propio del municipio, en el cociente peronismo / derecha.
      const draw = () => (gl ? R.t(gl) : R.normal());
      for (let k = 0; k < nS; k++) uS[k] = draw();
      for (let j = 0; j < M; j++) e[j] = cSec[j] * uS[secDeMuni[j]] + sigPropio[j] * draw();
      for (let i = 0; i < n; i++) {
        const f = e[muni[i]];
        s[i * K] *= Math.exp(f / 2); s[i * K + 1] *= Math.exp(-f / 2);
        let t = 0;
        for (let k = 0; k < K; k++) t += s[i * K + k];
        for (let k = 0; k < K; k++) s[i * K + k] /= t;
      }
      const sf = proporcional(s, w, S, n, K, 40);
      // Votos nativos por circuito.
      let nat = new Float64Array(n * KK);
      const col = (i, k) => (perfil ? Math.max(sf[i * K + k] * vBase[i] + perfil[k] * dV[i], 0) : sf[i * K + k] * votantes[i]);
      let extK = ext;
      if (!dividida) {
        for (let i = 0; i < n; i++) for (let k = 0; k < K; k++) nat[i * KK + k] = col(i, k);
      } else {
        const obj = Math.min(Math.max(o.piProv + R.normal() * (o.sdPi || 0), 0.01), 0.99);
        const ruidoM = Float64Array.from(sigPi, (sg) => R.t(GL) * sg);
        const der = new Float64Array(n);
        let Dtot = 0;
        for (let i = 0; i < n; i++) { der[i] = col(i, 1); Dtot += der[i]; }
        let lo = -10, hi = 10, mid = 0;
        for (let k = 0; k < 40; k++) {
          mid = (lo + hi) / 2;
          let s2 = 0;
          for (let i = 0; i < n; i++) s2 += der[i] / (1 + Math.exp(-(lg[i] + ruidoM[muni[i]] + mid)));
          if (s2 / Dtot < obj) lo = mid; else hi = mid;
        }
        const dM = new Float64Array(M), pM = new Float64Array(M);
        for (let i = 0; i < n; i++) {
          const pi = 1 / (1 + Math.exp(-(lg[i] + ruidoM[muni[i]] + mid)));
          nat[i * KK] = col(i, 0);
          nat[i * KK + 1] = der[i] * (1 - pi);
          nat[i * KK + 2] = der[i] * pi;
          for (let k = 2; k < K; k++) nat[i * KK + k + 1] = col(i, k);
          dM[muni[i]] += der[i]; pM[muni[i]] += der[i] * pi;
        }
        extK = new Float64Array(M * KK);
        for (let j = 0; j < M; j++) {
          const pim = pM[j] / Math.max(dM[j], 1);
          extK[j * KK] = ext[j * K];
          extK[j * KK + 1] = ext[j * K + 1] * (1 - pim);
          extK[j * KK + 2] = ext[j * K + 1] * pim;
          for (let k = 2; k < K; k++) extK[j * KK + k + 1] = ext[j * K + k];
        }
      }
      // Agregados.
      const vm = Float64Array.from(extK);
      for (let i = 0; i < n; i++) for (let k = 0; k < KK; k++) vm[muni[i] * KK + k] += nat[i * KK + k];
      const tot = new Float64Array(KK), vs = new Float64Array(nS * KK);
      let munisPer = 0;
      for (let j = 0; j < M; j++) {
        let best = 0, tm = 0;
        for (let k = 0; k < KK; k++) {
          const v = vm[j * KK + k];
          tot[k] += v; vs[secDeMuni[j] * KK + k] += v; tm += v;
          if (v > vm[j * KK + best]) best = k;
        }
        out.muniPrimero[j * KK + best] += 1;
        if (best === 0) munisPer++;
        for (let k = 0; k < KK; k++) out.muniSh[j * KK + k] += vm[j * KK + k] / tm;
      }
      const T = tot.reduce((a, b) => a + b, 0);
      const pct = Array.from(tot, (v) => 100 * v / T);
      out.R.push(pct);
      const rival = Math.max(...pct.slice(1));
      out.margen.push(dividida ? pct[0] - rival : pct[0] - pct[1]);
      out.munisPrimero.push(munisPer);
      const dip = new Array(KK).fill(0), sen = new Array(KK).fill(0);
      for (let k = 0; k < nS; k++) {
        let best = 0, ts = 0;
        const votos = {};
        for (let b = 0; b < KK; b++) {
          const v = vs[k * KK + b];
          votos[nombres[b]] = v; ts += v;
          if (v > vs[k * KK + best]) best = b;
        }
        out.secPrimero[k * KK + best] += 1;
        for (let b = 0; b < KK; b++) out.secSh[k * KK + b] += vs[k * KK + b] / ts;
        const sid = secIds[k], cam = L.camara_2027[sid];
        const asign = reparto(votos, cam === "DIP" ? L.dip[sid] : L.sen[sid], elegibles);
        const dest = cam === "DIP" ? dip : sen;
        for (const [nm, nb] of Object.entries(asign)) { dest[nombres.indexOf(nm)] += nb; out.secBancas[k * KK + nombres.indexOf(nm)] += nb; }
      }
      out.dip.push(dip); out.sen.push(sen);
    }
    for (const a of [out.muniPrimero, out.muniSh, out.secPrimero, out.secSh, out.secBancas]) for (let j = 0; j < a.length; j++) a[j] /= nSim;
    out.pGana = out.R.filter((r) => r.indexOf(Math.max(...r)) === 0).length / nSim;
    return out;
  }

  function percentil(a, p) {
    const s = [...a].sort((x, y) => x - y);
    const h = (s.length - 1) * p / 100, lo = Math.floor(h);
    return s[lo] + (s[Math.min(lo + 1, s.length - 1)] - s[lo]) * (h - lo);
  }

  const api = { rng, proporcional, uniforme, mezcla, escalarParticipacion, reparto, preparar, simular, percentil };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else raiz.Motor2027 = api;
})(typeof self !== "undefined" ? self : this);
