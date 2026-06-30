/**
 * three-background.js - Subtle Three.js animated background
 * Creates floating SQL words, database cylinders, and soft particles.
 * Light lavender theme - low opacity for readability.
 */

(function () {
  const canvas = document.getElementById('three-canvas');
  if (!canvas || typeof THREE === 'undefined') return;

  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setClearColor(0xF8F7FF, 0.0);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
  camera.position.z = 20;

  // ─── Lights ───
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.9);
  scene.add(ambientLight);

  const dirLight = new THREE.DirectionalLight(0xA78BFA, 0.5);
  dirLight.position.set(5, 10, 5);
  scene.add(dirLight);

  // ─── Colors ───
  const colors = [
    0xDDD6FE, // light purple
    0xC4B5FD, // medium purple
    0xDBEAFE, // soft blue
    0xFCE7F3, // soft pink
    0xEDE9FE  // lavender
  ];

  // ─── Particles ───
  const particleCount = window.innerWidth < 768 ? 60 : 150;
  const particleGeo = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const particleColors = new Float32Array(particleCount * 3);

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3] = (Math.random() - 0.5) * 60;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 40;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 20;

    const col = new THREE.Color(colors[Math.floor(Math.random() * colors.length)]);
    particleColors[i * 3] = col.r;
    particleColors[i * 3 + 1] = col.g;
    particleColors[i * 3 + 2] = col.b;
  }

  particleGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

  const particleMat = new THREE.PointsMaterial({
    size: 0.15,
    vertexColors: true,
    transparent: true,
    opacity: 0.55
  });

  const particles = new THREE.Points(particleGeo, particleMat);
  scene.add(particles);

  // ─── Database Cylinders ───
  const cylinders = [];
  const cylCount = window.innerWidth < 768 ? 3 : 7;

  for (let i = 0; i < cylCount; i++) {
    const group = new THREE.Group();
    const colHex = colors[Math.floor(Math.random() * colors.length)];
    const mat = new THREE.MeshPhongMaterial({
      color: colHex,
      transparent: true,
      opacity: 0.25,
      shininess: 40
    });

    const body = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.8, 20), mat);
    const top = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.1, 20), mat);
    const bottom = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.1, 20), mat);
    top.position.y = 0.45;
    bottom.position.y = -0.45;

    group.add(body, top, bottom);
    group.position.set(
      (Math.random() - 0.5) * 40,
      (Math.random() - 0.5) * 25,
      (Math.random() - 0.5) * 10 - 5
    );
    group.rotation.z = Math.random() * 0.5 - 0.25;

    group.userData = {
      floatSpeed: 0.003 + Math.random() * 0.004,
      rotSpeed: 0.005 + Math.random() * 0.005,
      floatOffset: Math.random() * Math.PI * 2
    };

    scene.add(group);
    cylinders.push(group);
  }

  // ─── Floating SQL Text Sprites ───
  const sqlWords = ['SELECT', 'JOIN', 'WHERE', 'GROUP BY', 'INDEX', 'TABLE', 'QUERY', 'WITH', 'HAVING', 'ORDER BY'];
  const textSprites = [];

  function makeTextSprite(text) {
    const c = document.createElement('canvas');
    c.width = 256; c.height = 64;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, 256, 64);
    ctx.font = 'bold 22px Fira Code, monospace';
    ctx.fillStyle = 'rgba(124, 58, 237, 0.35)';
    ctx.fillText(text, 10, 42);

    const texture = new THREE.CanvasTexture(c);
    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true, opacity: 0.55 });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(4, 1, 1);
    return sprite;
  }

  const wordCount = window.innerWidth < 768 ? 4 : 8;
  for (let i = 0; i < wordCount; i++) {
    const sprite = makeTextSprite(sqlWords[i % sqlWords.length]);
    sprite.position.set(
      (Math.random() - 0.5) * 40,
      (Math.random() - 0.5) * 25,
      (Math.random() - 0.5) * 8 - 5
    );
    sprite.userData = {
      floatSpeed: 0.002 + Math.random() * 0.003,
      floatOffset: Math.random() * Math.PI * 2
    };
    scene.add(sprite);
    textSprites.push(sprite);
  }

  // ─── Mouse Parallax ───
  let mouseX = 0, mouseY = 0;
  document.addEventListener('mousemove', e => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 2;
    mouseY = -(e.clientY / window.innerHeight - 0.5) * 2;
  });

  // ─── Animation Loop ───
  let frame = 0;
  function animate() {
    requestAnimationFrame(animate);
    frame += 0.01;

    // Gentle camera parallax
    camera.position.x += (mouseX * 2 - camera.position.x) * 0.03;
    camera.position.y += (mouseY * 1.5 - camera.position.y) * 0.03;
    camera.lookAt(scene.position);

    // Rotate particles slowly
    particles.rotation.y = frame * 0.04;
    particles.rotation.x = frame * 0.01;

    // Float cylinders
    cylinders.forEach(cyl => {
      cyl.position.y += Math.sin(frame * cyl.userData.floatSpeed * 10 + cyl.userData.floatOffset) * 0.01;
      cyl.rotation.y += cyl.userData.rotSpeed;
    });

    // Float text sprites
    textSprites.forEach(sp => {
      sp.position.y += Math.sin(frame * sp.userData.floatSpeed * 8 + sp.userData.floatOffset) * 0.008;
    });

    renderer.render(scene, camera);
  }

  animate();

  // ─── Resize handler ───
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

})();
