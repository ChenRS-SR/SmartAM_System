<template>
  <div class="subsystem-diagram">
    <!-- 统一新版立体图的画布与比例；引线独立叠加，不改变机器结构。 -->
    <svg viewBox="0 0 1280 698" role="img" :aria-label="description">
      <title>设备子系统健康状态</title>
      <image :href="machineImage" width="1280" height="698" preserveAspectRatio="xMidYMid meet" />
      <g v-for="(system,index) in systems" :key="system.key" :class="['system-part',system.state]" :data-system="system.key">
        <circle :cx="positions[index].anchor[0]" :cy="positions[index].anchor[1]" r="9" />
      </g>
      <g v-for="(system,index) in systems" :key="system.key" :class="['system-callout',system.state]">
        <polyline class="leader-halo" :points="positions[index].line"/>
        <polyline class="leader" :points="positions[index].line"/>
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
import { diagnosisArtwork } from '../diagnosisArtwork'
const props=defineProps({systems:{type:Array,required:true},processIssue:Boolean, diagnosisState:String, faults:{type:Array,default:()=>[]}})
const description=computed(()=>props.systems.map(s=>`${s.name}：${s.label}${s.details.length ? '，'+s.details.join('、') : ''}`).join('；'))
// 图像类别和引线共用诊断结果，不用子系统大类推测具体故障。
const machineImage=computed(()=>diagnosisArtwork({
  state:props.processIssue ? 'process' : props.diagnosisState,
  faults:props.faults,
  healthy:props.systems.every(s=>s.state==='normal'),
  equipmentIssue:props.systems.some(s=>s.state==='fault'),
}))
// 每条引线只有三个节点：部件锚点、斜线拐点、水平接入标签边缘。
const positions=[
  {x:10,y:190,line:'462,330 400,268 270,268',anchor:[462,330]},
  {x:1010,y:15,line:'668,166 741,93 1010,93',anchor:[668,166]},
  {x:1010,y:320,line:'886,473 961,398 1010,398',anchor:[886,473]},
  {x:10,y:500,line:'655,520 597,578 270,578',anchor:[655,520]},
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
.system-callout polyline { fill:none; vector-effect:non-scaling-stroke; stroke-linejoin:round; stroke-linecap:round; }
/* 浅色描边隔开机壳线稿，缩放后引线仍保持清晰。 */
.system-callout .leader-halo { stroke:var(--card-bg,#fff); stroke-width:4px; }
.system-callout .leader { stroke-width:1.7px; }
.system-callout.fault .leader { stroke-width:2px; }
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
