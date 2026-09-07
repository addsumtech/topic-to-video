// BRIDGE react-three-fiber's JSX AUGMENTATION TO THE NAMESPACE THIS PROJECT ACTUALLY COMPILES AGAINST.
//
// r3f v8 declares `<mesh>`, `<group>`, `<boxGeometry>` and the rest by augmenting the GLOBAL `JSX` namespace.
// Under `"jsx": "react-jsx"` with React 18's types, TypeScript resolves intrinsic elements from
// `React.JSX.IntrinsicElements` instead — a different interface — so every three.js tag in the two WebGL
// registers reported "Property 'mesh' does not exist". 53 errors of pure noise, which is exactly how a
// typecheck ends up being declared not worth running. Re-declaring the same extension where the compiler
// looks costs four lines and makes the gate's output all signal.
import type {ThreeElements} from '@react-three/fiber';

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements extends ThreeElements {}
  }
}
