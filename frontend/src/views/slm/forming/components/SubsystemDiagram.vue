<template>
  <div class="subsystem-diagram">
    <!-- 保留原始立体图的画布与比例；引线独立叠加，不改变机器结构。 -->
    <svg viewBox="0 0 1280 698" role="img" :aria-label="description">
      <title>设备子系统健康状态</title>
      <image :href="machineImage" width="1280" height="698" preserveAspectRatio="xMidYMid meet" />
      <g v-for="(system,index) in systems" :key="system.key" :class="['system-part',system.state]" :data-system="system.key">
        <circle :cx="positions[index].anchor[0]" :cy="positions[index].anchor[1]" r="9" />
      </g>
      <g v-for="(system,index) in systems" :key="system.key" :class="['system-callout',system.state]">
        <polyline :points="positions[index].line"/>
        <circle :cx="positions[index].anchor[0]" :cy="positions[index].anchor[1]" r="5"/>
        <g :transform="`translate(${positions[index].x},${positions[index].y})`">
          <rect width="260" height="155" rx="5"/>
          <text x="15" y="32" class="system-name">{{ system.name }}</text>
          <text x="15" y="65" class="system-status">{{ system.label }}</text>
          <text v-for="(detail,i) in system.details" :key="detail" x="15" :y="93+i*23" class="fault-label">{{ detail }}</text>
        </g>
      </g>
      <text x="640" y="680" class="machine-caption" text-anchor="middle">{{ processIssue ? '工艺问题引发异常' : '设备子系统状态' }}</text>
    </svg>
    <div class="health-list" aria-label="子系统健康状态列表">
      <div v-for="system in systems" :key="system.key" :class="system.state">
        <strong>{{ system.name }}</strong><span>{{ system.label }}</span>
        <p v-if="system.details.length">{{ system.details.join('、') }}</p>
      </div>
    </div>
    <div class="diagram-legend"><span class="normal">正常</span><span class="fault">异常</span><span class="unknown">未接入</span></div>
  </div>
</template>
<script setup>
import { computed } from 'vue'
const props=defineProps({systems:{type:Array,required:true},processIssue:Boolean})
const description=computed(()=>props.systems.map(s=>`${s.name}：${s.label}${s.details.length ? '，'+s.details.join('、') : ''}`).join('；'))
// 复用原有预制立体图，未知状态保持中性，不能将未接入误标成健康。
const machineImage=computed(()=>{
  const faults=props.systems.filter(s=>s.state==='fault').map(s=>s.key)
  if (props.processIssue) return '/state_picture/power_off.png'
  if (faults.length>1) return '/state_picture/fault_multi.png'
  const images={powder:'fault_powder',optics:'fault_laser',gas:'fault_gas'}
  if (faults.length===1 && images[faults[0]]) return `/state_picture/${images[faults[0]]}.png`
  if (props.systems.every(s=>s.state==='normal')) return '/state_picture/health.png'
  return '/state_picture/power_off.png'
})
const positions=[
  {x:10,y:190,line:'462,330 285,330 285,268 270,268',anchor:[462,330]},
  {x:1010,y:15,line:'668,166 965,166 990,93 1010,93',anchor:[668,166]},
  {x:1010,y:320,line:'886,473 990,473 990,398 1010,398',anchor:[886,473]},
  {x:10,y:460,line:'655,520 285,520 285,538 270,538',anchor:[655,520]},
]
</script>
<style scoped>
.subsystem-diagram { min-width:0; }
svg { display:block; width:100%; height:auto; }
.system-part { stroke-width:3; transition:fill .2s,stroke .2s; }
.system-part.unknown { fill:#dce2e8; stroke:#8393a3; }
.system-part.normal { fill:#cce7db; stroke:#27825e; }
.system-part.fault { fill:#efb7b3; stroke:#bd423b; }
.system-callout { stroke-width:2; }
.system-callout polyline { fill:none; }
.system-callout rect { fill:var(--card-bg,#fff); }
.system-callout.unknown { stroke:#8795a3; fill:#8795a3; }
.system-callout.normal { stroke:#27825e; fill:#27825e; }
.system-callout.fault { stroke:#bd423b; fill:#bd423b; }
text { stroke:none; font-family:inherit; }
.system-name { font-size:21px; font-weight:600; fill:var(--text,#243b53); }
.system-status { font-size:21px; font-weight:700; }
.fault-label { font-size:18px; fill:var(--text,#243b53); }
.machine-caption { font-size:20px; fill:var(--text-2,#52677d); }
.diagram-legend { display:flex; justify-content:center; gap:20px; font-size:12px; padding:8px; }
.diagram-legend span::before { content:''; display:inline-block; width:9px; height:9px; margin-right:5px; background:currentColor; }
.normal { color:#27825e; }.fault { color:#bd423b; }.unknown { color:#8795a3; }
.health-list { display:none; }
@media(max-width:767px) {
  .health-list { display:grid; grid-template-columns:minmax(0,1fr); gap:8px; font-size:13px; }
  .health-list > div { padding:10px; border:1px solid var(--border); display:flex; flex-wrap:wrap; gap:8px; }
  .health-list strong { flex:1; color:var(--text); }.health-list p { margin:0; width:100%; }
}
</style>
