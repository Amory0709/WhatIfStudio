"use client";

import { useEffect, useRef } from 'react';

// Abstract light field, rendered below the interactive gallery. No image
// readback or external textures; the CSS background is the WebGL fallback.
const fragment = `
precision mediump float;
uniform vec2 resolution;
uniform vec2 pointer;
uniform float time;
float sq(float v) { return v * v; }
void main() {
  vec2 uv = gl_FragCoord.xy / resolution;
  vec2 p = (uv - .5) * vec2(resolution.x / resolution.y, 1.);
  p += pointer * .025;
  float t = time * .16;
  float flow = sin(p.y * 4. + t) * .11 + sin(p.y * 8. - t * .7) * .035;
  float radius = .43 + .13 * cos(p.y * 5. + t * .5);
  float d = abs(p.x + flow) - radius;
  float band = exp(-sq(d * 12.));
  float rim = exp(-sq((d + .046) * 95.));
  float inner = exp(-sq((d - .025) * 47.));
  vec3 spectrum = .55 + .45 * cos(6.28318 * (p.y * .6 + p.x * .3 + t * .09 + vec3(.05, .36, .65)));
  vec3 col = vec3(.971, .978, .991);
  col = mix(col, spectrum, band * .34);
  col = mix(col, vec3(.18, .49, .98), inner * .12);
  col = mix(col, vec3(1.), rim * .95);
  float caustic = exp(-sq((d + .085) * 37.));
  col += caustic * .075;
  // Keep the active portrait and its caption on a quiet, luminous center.
  float center = exp(-dot(p * vec2(2.3, 1.2), p * vec2(2.3, 1.2)) * 3.);
  col = mix(col, vec3(.984, .986, .994), center * .5);
  gl_FragColor = vec4(col, 1.);
}`;

export function LiquidLight() {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const gl = canvas.getContext('webgl', { alpha: false, antialias: false, powerPreference: 'low-power' });
    if (!gl) return;
    const compile = (type: number, source: string) => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    };
    const vertex = compile(gl.VERTEX_SHADER, 'attribute vec2 position; void main(){gl_Position=vec4(position,0.,1.);}');
    const pixel = compile(gl.FRAGMENT_SHADER, fragment);
    const program = gl.createProgram();
    if (!vertex || !pixel || !program) {
      if (vertex) gl.deleteShader(vertex);
      if (pixel) gl.deleteShader(pixel);
      if (program) gl.deleteProgram(program);
      return;
    }
    gl.attachShader(program, vertex);
    gl.attachShader(program, pixel);
    gl.linkProgram(program);
    gl.deleteShader(vertex);
    gl.deleteShader(pixel);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      gl.deleteProgram(program);
      return;
    }
    gl.useProgram(program);
    const buffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1,-1, 1,-1, -1,1, -1,1, 1,-1, 1,1]), gl.STATIC_DRAW);
    const position = gl.getAttribLocation(program, 'position');
    gl.enableVertexAttribArray(position);
    gl.vertexAttribPointer(position, 2, gl.FLOAT, false, 0, 0);
    const size = gl.getUniformLocation(program, 'resolution');
    const clock = gl.getUniformLocation(program, 'time');
    const mouse = gl.getUniformLocation(program, 'pointer');
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let frame = 0;
    let last = -Infinity;
    let x = 0, y = 0, targetX = 0, targetY = 0;
    let disposed = false;
    const draw = (now: number) => {
      if (disposed || document.hidden || gl.isContextLost()) return;
      // Cap the decorative pass at 30 fps and a 1.25 pixel ratio.
      if (now - last >= 32 || reduced.matches) {
        x += (targetX - x) * .045;
        y += (targetY - y) * .045;
        gl.uniform2f(size, canvas.width, canvas.height);
        gl.uniform2f(mouse, reduced.matches ? 0 : x, reduced.matches ? 0 : y);
        gl.uniform1f(clock, reduced.matches ? 0 : now / 1000);
        gl.drawArrays(gl.TRIANGLES, 0, 6);
        canvas.style.opacity = '1';
        last = now;
      }
      if (!reduced.matches) frame = requestAnimationFrame(draw);
    };
    const restart = () => {
      cancelAnimationFrame(frame);
      last = -Infinity;
      draw(performance.now());
    };
    const resize = () => {
      const ratio = Math.min(window.devicePixelRatio || 1, 1.25);
      canvas.width = Math.max(1, Math.round(canvas.clientWidth * ratio));
      canvas.height = Math.max(1, Math.round(canvas.clientHeight * ratio));
      gl.viewport(0, 0, canvas.width, canvas.height);
      restart();
    };
    const move = (event: PointerEvent) => {
      targetX = event.clientX / window.innerWidth - .5;
      targetY = .5 - event.clientY / window.innerHeight;
    };
    const lost = (event: Event) => {
      event.preventDefault();
      cancelAnimationFrame(frame);
      canvas.style.opacity = '0';
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    window.addEventListener('pointermove', move, { passive: true });
    document.addEventListener('visibilitychange', restart);
    reduced.addEventListener('change', restart);
    canvas.addEventListener('webglcontextlost', lost);
    resize();
    return () => {
      disposed = true;
      cancelAnimationFrame(frame);
      observer.disconnect();
      window.removeEventListener('pointermove', move);
      document.removeEventListener('visibilitychange', restart);
      reduced.removeEventListener('change', restart);
      canvas.removeEventListener('webglcontextlost', lost);
      gl.deleteBuffer(buffer);
      gl.deleteProgram(program);
    };
  }, []);

  return <div className="liquid-light" aria-hidden="true"><canvas ref={ref} /></div>;
}
