<template><div ref="el" class="echart"></div></template>
<script setup>
import { onMounted, onBeforeUnmount, ref, watch } from 'vue'
import * as echarts from 'echarts'
const props = defineProps({ option: { type: Object, required: true } })
const el = ref(null)
let chart = null
let ro = null
onMounted(() => {
  chart = echarts.init(el.value, null, { renderer: 'canvas' })
  chart.setOption(props.option)
  ro = new ResizeObserver(() => chart && chart.resize())  // 嵌入其他系统时随容器尺寸变化
  ro.observe(el.value)
})
watch(() => props.option, (o) => chart && chart.setOption(o, true))
onBeforeUnmount(() => { ro && ro.disconnect(); chart && chart.dispose() })
</script>
<style scoped>.echart { width: 100%; height: 100%; }</style>
