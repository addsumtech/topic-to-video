// 'three' inside the splat add-on (stage3d_splat.js): the THREE that stage3d.js already carries, so a page has ONE three
// and a SplatMesh is an Object3D of the stage's own scene. stage3d.js must load first.
if (typeof window === 'undefined' || !window.Stage3D || !window.Stage3D.THREE) throw new Error('stage3d_splat.js: load stage3d.js before it');
module.exports = window.Stage3D.THREE;
