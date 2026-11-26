// The splat add-on, built into assets/html/stage3d_splat.js (scripts/build_stage3d.sh): Spark (@sparkjsdev/spark, MIT,
// World Labs), the Gaussian-splat renderer, on the stage's own three. A page that shows a scan loads it after
// stage3d.js; st.splat() (src.js) uses it. Kept out of stage3d.js: ~2.8 MB that no other film needs.
export {SparkRenderer, SplatMesh} from '@sparkjsdev/spark';
