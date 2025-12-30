<script setup lang="ts">
/**
 * @fileoverview 水球动画组件 (WaterBall)
 * @description 使用 Three.js 实现的 3D 水球动画，用于可视化语音交互状态。
 *              根据当前的交互状态 (监听、说话、处理中) 改变水球的波动幅度、颜色和粒子效果。
 */

import { onMounted, onUnmounted, ref } from 'vue';
import * as THREE from 'three';

// --- Props 定义 ---

const props = defineProps<{
  /** 是否正在监听用户语音 */
  isListening: boolean;
  /** AI 是否正在说话 */
  isSpeaking: boolean;
  /** 是否正在处理/思考中 */
  isProcessing: boolean;
}>();

// --- 内部状态 ---

const containerRef = ref<HTMLElement | null>(null);
let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let sphere: THREE.Mesh;
let particles: THREE.Points[] = [];
let animationId: number;

// --- Three.js 初始化 ---

/**
 * 初始化 3D 场景
 * 
 * 创建场景、相机、渲染器、光源，并添加水球和粒子系统。
 */
const initScene = () => {
  if (!containerRef.value) return;

  // 1. 创建场景
  scene = new THREE.Scene();

  // 2. 创建相机
  camera = new THREE.PerspectiveCamera(75, containerRef.value.clientWidth / containerRef.value.clientHeight, 0.1, 1000);
  camera.position.z = 250;

  // 3. 创建渲染器 (开启抗锯齿和透明背景)
  renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: true,
    powerPreference: "high-performance"
  });
  renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight);
  renderer.setPixelRatio(window.devicePixelRatio);
  containerRef.value.appendChild(renderer.domElement);

  // 4. 创建物体
  createWaterBall();
  createParticleSystem();

  // 5. 添加光源
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
  scene.add(ambientLight);

  const pointLight1 = new THREE.PointLight(0x6366f1, 1.5, 300);
  pointLight1.position.set(100, 100, 100);
  scene.add(pointLight1);

  const pointLight2 = new THREE.PointLight(0x8b5cf6, 1.5, 300);
  pointLight2.position.set(-100, -100, 100);
  scene.add(pointLight2);

  // 6. 开始动画循环
  animate();

  // 监听窗口大小变化
  window.addEventListener('resize', handleResize);
};

/**
 * 处理窗口大小调整
 * 
 * 更新相机纵横比和渲染器尺寸。
 */
const handleResize = () => {
  if (!containerRef.value || !camera || !renderer) return;
  camera.aspect = containerRef.value.clientWidth / containerRef.value.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(containerRef.value.clientWidth, containerRef.value.clientHeight);
};

/**
 * 创建水球网格
 * 
 * 使用 SphereGeometry 和 ShaderMaterial (自定义着色器) 实现波动效果。
 */
const createWaterBall = () => {
  const geometry = new THREE.SphereGeometry(80, 64, 64);
  const material = new THREE.ShaderMaterial({
    uniforms: {
      time: { value: 0 },
      color1: { value: new THREE.Color(0x6366f1) }, // 靛蓝色
      color2: { value: new THREE.Color(0x8b5cf6) }, // 紫色
      color3: { value: new THREE.Color(0x3b82f6) }  // 蓝色
    },
    // 顶点着色器：实现波浪形变
    vertexShader: `
      uniform float time;
      varying vec2 vUv;
      varying vec3 vNormal;
      varying vec3 vPosition;
      
      void main() {
        vUv = uv;
        vNormal = normalize(normalMatrix * normal);
        
        vec3 pos = position;
        // 叠加多个正弦波实现复杂的波动效果
        float wave1 = sin(pos.x * 0.05 + time) * 3.0;
        float wave2 = cos(pos.y * 0.05 + time * 1.2) * 3.0;
        float wave3 = sin(pos.z * 0.05 + time * 0.8) * 2.0;
        
        pos += normal * (wave1 + wave2 + wave3);
        vPosition = pos;
        
        gl_Position = projectionMatrix * modelViewMatrix * vec4(pos, 1.0);
      }
    `,
    // 片元着色器：实现颜色渐变和光照
    // 片元着色器：实现颜色渐变和光照
    fragmentShader: `
      uniform float time;
      uniform vec3 color1;
      uniform vec3 color2;
      uniform vec3 color3;
      varying vec2 vUv;
      varying vec3 vNormal;
      varying vec3 vPosition;
      
      void main() {
        vec3 viewDirection = normalize(cameraPosition - vPosition);
        // 菲涅尔效应：边缘发光
        float fresnel = pow(1.0 - abs(dot(viewDirection, vNormal)), 3.0);
        
        // 动态颜色混合
        float mixValue1 = sin(vPosition.y * 0.01 + time * 0.5) * 0.5 + 0.5;
        float mixValue2 = cos(vPosition.x * 0.01 + time * 0.3) * 0.5 + 0.5;
        
        vec3 color = mix(color1, color2, mixValue1);
        color = mix(color, color3, mixValue2);
        
        // 叠加菲涅尔光
        color = mix(color, vec3(1.0), fresnel * 0.4);
        
        // 高光效果
        float gloss = pow(max(dot(vNormal, viewDirection), 0.0), 32.0);
        color += vec3(gloss * 0.5);
        
        gl_FragColor = vec4(color, 0.9);
      }
    `,
    transparent: true,
    side: THREE.DoubleSide
  });

  sphere = new THREE.Mesh(geometry, material);
  scene.add(sphere);
};

/**
 * 创建粒子系统
 * 
 * 在水球周围创建漂浮的粒子，增加氛围感。
 */
const createParticleSystem = () => {
  const particleCount = 200;
  const geometry = new THREE.BufferGeometry();
  const positions = [];
  const colors = [];

  for (let i = 0; i < particleCount; i++) {
    // 随机分布在球体周围
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.random() * Math.PI;
    const radius = 100 + Math.random() * 50;

    const x = radius * Math.sin(phi) * Math.cos(theta);
    const y = radius * Math.sin(phi) * Math.sin(theta);
    const z = radius * Math.cos(phi);

    positions.push(x, y, z);

    // 随机颜色
    const color = new THREE.Color();
    color.setHSL(0.6 + Math.random() * 0.1, 0.8, 0.6);
    colors.push(color.r, color.g, color.b);
  }

  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));

  const material = new THREE.PointsMaterial({
    size: 3,
    vertexColors: true,
    transparent: true,
    opacity: 0.6,
    blending: THREE.AdditiveBlending
  });

  const particleSystem = new THREE.Points(geometry, material);
  scene.add(particleSystem);
  particles.push(particleSystem);
};

/**
 * 动画循环
 * 
 * 每帧更新水球的形态、旋转和颜色，响应 props 的状态变化。
 */
const animate = () => {
  animationId = requestAnimationFrame(animate);

  const time = Date.now() * 0.001;

  // 更新 Shader 时间变量
  if (sphere && (sphere.material as THREE.ShaderMaterial).uniforms) {
    (sphere.material as THREE.ShaderMaterial).uniforms.time.value = time;
  }

  // 基础自转
  if (sphere) {
    sphere.rotation.y = time * 0.2;
    sphere.rotation.x = Math.sin(time * 0.3) * 0.1;
  }

  // 根据状态调整动画效果
  if (props.isListening && sphere) {
    // 监听状态：呼吸效果 (红色调)
    const scale = 1 + Math.sin(time * 5) * 0.1;
    sphere.scale.set(scale, scale, scale);
    (sphere.material as THREE.ShaderMaterial).uniforms.color1.value.setHex(0xff4444); 
  } else if (props.isSpeaking && sphere) {
    // 说话状态：快速震动 (绿色调)
    const scale = 1 + Math.sin(time * 10) * 0.05;
    sphere.scale.set(scale, scale, scale);
    (sphere.material as THREE.ShaderMaterial).uniforms.color1.value.setHex(0x44ff44); 
  } else if (props.isProcessing && sphere) {
    // 处理状态：快速旋转 (黄色调)
    sphere.rotation.y = time * 2;
    (sphere.material as THREE.ShaderMaterial).uniforms.color1.value.setHex(0xffff44); 
  } else {
    // 空闲状态：恢复默认
    if (sphere) {
      sphere.scale.set(1, 1, 1);
      (sphere.material as THREE.ShaderMaterial).uniforms.color1.value.setHex(0x6366f1); // Original
    }
  }

  // 粒子系统旋转
  particles.forEach((ps, index) => {
    ps.rotation.y = time * (0.1 + index * 0.05);
    ps.rotation.x = time * 0.05;
  });

  // 执行渲染
  if (renderer && scene && camera) {
    renderer.render(scene, camera);
  }
};

// --- 生命周期 ---

onMounted(() => {
  initScene();
});

onUnmounted(() => {
  // 清理资源
  cancelAnimationFrame(animationId);
  window.removeEventListener('resize', handleResize);
  if (renderer) {
    renderer.dispose();
  }
});
</script>

<template>
  <div ref="containerRef" class="w-full h-full"></div>
</template>
