<script setup lang="ts">
import { computed } from 'vue';

const props = defineProps<{
  score: number; // 0-100
}>();

const stars = computed(() => {
  const percentage = Math.min(100, Math.max(0, props.score));
  // 5 stars, each represents 20 points
  // We need to calculate the fill percentage for each star
  
  return Array.from({ length: 5 }, (_, i) => {
    const starValue = (i + 1) * 20;
    const prevStarValue = i * 20;
    
    if (percentage >= starValue) {
      return 100; // Full star
    } else if (percentage > prevStarValue) {
      return ((percentage - prevStarValue) / 20) * 100; // Partial star
    } else {
      return 0; // Empty star
    }
  });
});
</script>

<template>
  <div class="flex items-center space-x-1" title="Score: {{ score }}/100">
    <div v-for="(fill, index) in stars" :key="index" class="relative w-6 h-6">
      <!-- Empty Star Background -->
      <svg class="w-full h-full text-gray-700" fill="currentColor" viewBox="0 0 24 24">
        <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
      </svg>
      
      <!-- Filled Star Overlay -->
      <div class="absolute top-0 left-0 h-full overflow-hidden" :style="{ width: fill + '%' }">
        <svg class="w-6 h-6 text-yellow-400" fill="currentColor" viewBox="0 0 24 24">
          <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
        </svg>
      </div>
    </div>
    <span class="ml-2 text-yellow-400 font-bold text-lg">{{ score }}</span>
  </div>
</template>
