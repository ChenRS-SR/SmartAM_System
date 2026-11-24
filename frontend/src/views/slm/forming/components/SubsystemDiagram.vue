<template>
  <div class="subsystem-diagram">
    <!-- 整机结构为矢量示意，状态色、引线与类别由同一份诊断快照驱动。 -->
    <svg viewBox="0 0 1080 650" role="img" :aria-label="description">
      <title>设备子系统健康状态</title>
      <defs><linearGradient id="machine-metal" x2="1" y2="1"><stop stop-color="#f3f5f7"/><stop offset="1" stop-color="#cad2db"/></linearGradient></defs>
      <g class="machine">
        <path d="M300 150L390 105H720L790 155V535L720 575H300Z" fill="url(#machine-metal)"/>
        <path d="M300 150H720V575M720 150L790 155M720 575V150M300 535H720"/>
        <rect x="325" y="185" width="290" height="275" rx="5" fill="#f7f9fb"/>
        <rect x="642" y="195" width="55" height="80" rx="3" fill="#304860"/>
        <path d="M330 550V590H385V575M645 575V590H700V575"/>
      </g>
      <g :class="['system-part',systems[0].state]" data-system="powder">
        <path d="M345 270H410L395 310H360Z"/><rect x="357" y="311" width="42" height="22"/>
        <path d="M350 355H590V369H350ZM465 335H500V390H465Z"/>
        <rect x="350" y="395" width="240" height="25"/><path d="M365 430H575V445H365Z"/>
      </g>
      <g :class="['system-part',systems[1].state]" data-system="optics">
        <rect x="420" y="120" width="150" height="45" rx="3"/><path d="M495 165V205H555V245L540 265H510L495 245Z"/>
        <path class="beam" d="M525 265L480 390M525 265L545 390"/>
      </g>
      <g :class="['system-part',systems[2].state]" data-system="gas">
        <rect x="635" y="320" width="65" height="115" rx="8"/>
        <path d="M645 340V415M657 340V415M669 340V415M681 340V415M635 345H600V385M700 405H755V475H590"/>
        <circle cx="665" cy="475" r="28"/><path d="M665 451V499M641 475H689"/>
      </g>
      <g :class="['system-part',systems[3].state]" data-system="other">
        <rect x="340" y="480" width="150" height="50" rx="3"/><path d="M355 492H475V502H355V512H475M490 505H535V445"/>
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
      <text x="540" y="635" class="machine-caption" text-anchor="middle">{{ processIssue ? '工艺问题引发异常' : '设备子系统状态' }}</text>
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
const positions=[
  {x:5,y:235,line:'378,322 285,322 285,313 265,313',anchor:[378,322]},
  {x:815,y:20,line:'505,143 770,143 790,97 815,97',anchor:[505,143]},
  {x:815,y:275,line:'668,365 780,365 790,352 815,352',anchor:[668,365]},
  {x:5,y:445,line:'410,505 280,505 265,522',anchor:[410,505]},
]
</script>
<style scoped>
.subsystem-diagram { min-width:0; }
svg { display:block; width:100%; height:auto; }
.machine { stroke:#66788b; stroke-width:2; fill:none; }
.system-part { stroke-width:3; transition:fill .2s,stroke .2s; }
.system-part.unknown { fill:#dce2e8; stroke:#8393a3; }
.system-part.normal { fill:#cce7db; stroke:#27825e; }
.system-part.fault { fill:#efb7b3; stroke:#bd423b; }
.beam { fill:none; stroke-dasharray:7 5; }
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
