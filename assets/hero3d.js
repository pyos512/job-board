/* ============================================================
   히어로 3D 배경 (Three.js, 자체 호스팅)
   - 따뜻한 베이지/골드 톤의 저폴리 결정체 + 입자
   - 마우스 패럴랙스, 반응형, prefers-reduced-motion 시 정지
   - THREE 미로딩(오프라인 등) 시 조용히 종료 → 페이지 정상 동작
   ============================================================ */
(function () {
  "use strict";
  var canvas = document.getElementById("bg3d");
  if (!canvas || typeof THREE === "undefined") return;

  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var renderer = new THREE.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true });
  renderer.setClearColor(0x000000, 0);
  var scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0xf3ead6, 0.045);

  var camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
  camera.position.set(0, 0, 14);

  // 조명 — 따뜻한 톤
  scene.add(new THREE.AmbientLight(0xfff4dd, 0.85));
  var key = new THREE.DirectionalLight(0xffd9a0, 1.1); key.position.set(6, 8, 10); scene.add(key);
  var rim = new THREE.DirectionalLight(0x2f8f76, 0.6); rim.position.set(-8, -4, 6); scene.add(rim);

  var palette = [0x1f6f5c, 0xc8772e, 0xb8893b, 0xe7c887, 0x3a9b80];
  var shapes = [];
  var geos = [
    new THREE.IcosahedronGeometry(1, 0),
    new THREE.OctahedronGeometry(1, 0),
    new THREE.DodecahedronGeometry(1, 0),
    new THREE.TetrahedronGeometry(1, 0)
  ];
  var N = window.innerWidth < 600 ? 9 : 16;
  for (var i = 0; i < N; i++) {
    var g = geos[i % geos.length];
    var mat = new THREE.MeshStandardMaterial({
      color: palette[i % palette.length],
      roughness: 0.45, metalness: 0.25,
      flatShading: true, transparent: true, opacity: 0.92
    });
    var mesh = new THREE.Mesh(g, mat);
    var s = 0.5 + Math.random() * 1.5;
    mesh.scale.set(s, s, s);
    mesh.position.set((Math.random() - 0.5) * 22, (Math.random() - 0.5) * 12, (Math.random() - 0.5) * 10 - 2);
    mesh.userData = {
      rx: (Math.random() - 0.5) * 0.006, ry: (Math.random() - 0.5) * 0.006,
      fy: 0.2 + Math.random() * 0.5, ph: Math.random() * Math.PI * 2, baseY: mesh.position.y
    };
    scene.add(mesh); shapes.push(mesh);
  }

  // 입자 (반짝이는 먼지)
  var pGeo = new THREE.BufferGeometry();
  var pCount = window.innerWidth < 600 ? 120 : 260, pos = new Float32Array(pCount * 3);
  for (var p = 0; p < pCount; p++) {
    pos[p * 3] = (Math.random() - 0.5) * 30;
    pos[p * 3 + 1] = (Math.random() - 0.5) * 18;
    pos[p * 3 + 2] = (Math.random() - 0.5) * 14;
  }
  pGeo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  var particles = new THREE.Points(pGeo, new THREE.PointsMaterial({
    color: 0xb8893b, size: 0.08, transparent: true, opacity: 0.5
  }));
  scene.add(particles);

  var mx = 0, my = 0, tmx = 0, tmy = 0;
  window.addEventListener("mousemove", function (e) {
    tmx = (e.clientX / window.innerWidth - 0.5);
    tmy = (e.clientY / window.innerHeight - 0.5);
  }, { passive: true });

  function resize() {
    var h = canvas.parentElement;
    var w = h.clientWidth, ht = h.clientHeight || 420;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(w, ht, false);
    camera.aspect = w / ht; camera.updateProjectionMatrix();
  }
  window.addEventListener("resize", resize); resize();

  var t = 0;
  function frame() {
    t += 0.01;
    mx += (tmx - mx) * 0.05; my += (tmy - my) * 0.05;
    for (var i = 0; i < shapes.length; i++) {
      var m = shapes[i], u = m.userData;
      m.rotation.x += u.rx; m.rotation.y += u.ry;
      m.position.y = u.baseY + Math.sin(t * u.fy + u.ph) * 0.6;
    }
    particles.rotation.y += 0.0006;
    camera.position.x += (mx * 4 - camera.position.x) * 0.05;
    camera.position.y += (-my * 2.5 - camera.position.y) * 0.05;
    camera.lookAt(0, 0, 0);
    renderer.render(scene, camera);
    if (!reduce) requestAnimationFrame(frame);
  }
  frame();
})();
