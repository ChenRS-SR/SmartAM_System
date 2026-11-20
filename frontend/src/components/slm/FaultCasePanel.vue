<template>
  <div class="fault-case-panel">
    <RegionControlPanel v-if="module === 'control'" :key="device.id" :frame="controlFrame" :slice="data.slice" />
    <template v-else>
      <section class="fault-card fault-heading"><strong>{{ device.name }}</strong><span>设备状态：异常</span><span>{{ data.status }}</span></section>
      <div class="fault-content">
        <section v-if="module === 'trace'" class="fault-card diagnosis-card">
          <h2>故障诊断</h2>
          <figure><img :src="`/state_picture/${data.image}`" alt="设备诊断图" /><figcaption><span>诊断结论</span><strong>{{ data.status }}</strong></figcaption></figure>
          <p class="check-advice">{{ data.advice }}</p>
        </section>
        <section class="fault-card">
          <h2>{{ data.media.length ? '成形过程图像' : '切片区域' }}</h2>
          <div v-if="data.media.length" class="media-grid">
            <label v-for="media in data.media" :key="media.url">{{ media.name }}<video :src="media.url" controls autoplay muted loop playsinline preload="metadata" /></label>
          </div>
          <img v-else class="slice-illustration" :src="data.slice.annotatedImage" alt="切片区域引线示意图" />
        </section>
      </div>
      <section v-if="module !== 'access'" class="fault-card">
        <h2>{{ module === 'recognition' ? '缺陷识别记录' : '诊断记录' }}</h2>
        <div class="result-summary"><span>{{ data.control.side === 'proc' ? '工艺问题' : '设备问题' }}</span><strong>{{ data.status }}</strong></div>
        <ul v-if="data.diagnosis.evidence.length" class="evidence"><li v-for="(item,index) in data.diagnosis.evidence" :key="index">{{ item.text }}</li></ul>
        <p v-else>{{ data.advice }}</p>
      </section>
      <section v-if="module === 'access'" class="fault-card">
        <h2>设备状态参数</h2>
        <div class="parameter-grid"><div v-for="p in parameters" :key="p.id || p.name"><span>{{ p.name }}</span><strong>{{ p.value }} <small>{{ p.unit }}</small></strong></div></div>
      </section>
      <section v-if="data.records.length" class="fault-card">
        <h2>采集记录</h2>
        <div class="record-scroll" tabindex="0" role="region" aria-label="设备采集记录"><table><thead><tr><th v-for="key in columns" :key="key">{{ key }}</th></tr></thead><tbody><tr v-for="(row,i) in data.records.slice(-50)" :key="i"><td v-for="key in columns" :key="key">{{ row[key] }}</td></tr></tbody></table></div>
      </section>
    </template>
  </div>
</template>
<script setup>
import { computed } from 'vue'
import RegionControlPanel from './RegionControlPanel.vue'
const props = defineProps({ device: {type:Object,required:true}, data:{type:Object,required:true}, module:String, parameters:{type:Array,default:()=>[]} })
const columns = computed(() => Object.keys(props.data.records[0] || {}).filter(k=>k.trim()))
// 故障档案提供明确的演示触发方向，不将规则标签伪造成模型概率或因果贡献。
const controlFrame = computed(() => ({caseId:props.device.id, layer:props.parameters.find(p=>p.id==='current_layer')?.value || 1, controlSignal:props.data.control}))
</script>
<style scoped>
.fault-case-panel { min-width: 0; }
.fault-card { border: 1px solid var(--am-card-border); border-radius: 4px; padding: 18px; margin-bottom: 16px; background: var(--am-card-bg); min-width: 0; color: var(--am-text); }
h2 { margin: 0 0 16px; font-size: 16px; }
.fault-heading { display: flex; flex-wrap: wrap; gap: 12px 24px; }
.fault-heading span { color: var(--am-text-2); }
.fault-content { display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,360px),1fr)); gap: 16px; }
.slice-illustration { width: 100%; height: 320px; object-fit: contain; background: white; }
.media-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(min(100%,250px),1fr)); gap: 12px; }
.media-grid label { font-size: 13px; }
video { display: block; width: 100%; margin-top: 10px; background: #111; }
figure { margin: 0; border: 1px solid var(--am-card-border); padding: 12px; }
figure img { display: block; height: 260px; width: 100%; object-fit: contain; }
figcaption { display: flex; flex-direction: column; text-align: center; padding: 12px; gap: 8px; background: var(--am-card-bg-2); }
figcaption span { font-size: 12px; color: var(--am-text-2); }
figcaption strong { font-size: 20px; }
.check-advice { margin: 14px 0 0; text-align: center; font-weight: 600; line-height: 1.8; }
.result-summary { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.evidence { line-height: 1.9; margin-bottom: 0; }
.parameter-grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(160px,1fr)); gap: 12px; }
.parameter-grid div { display: flex; flex-direction: column; gap: 8px; padding: 12px; background: var(--am-card-bg-2); }
.parameter-grid span { font-size: 12px; color: var(--am-text-2); }
.parameter-grid strong { overflow-wrap: anywhere; }
.record-scroll { overflow: auto; max-height: 320px; }
table { border-collapse: collapse; width: 100%; white-space: nowrap; font-size: 13px; }
th,td { padding: 10px 14px; border-bottom: 1px solid var(--am-card-border); text-align: left; }
th { position: sticky; top: 0; background: var(--am-card-bg-2); }
</style>
