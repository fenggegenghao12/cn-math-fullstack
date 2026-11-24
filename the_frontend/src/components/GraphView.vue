<template>
  <div class="graph-wrapper">
    <!-- 控制面板（全宽在最上面） -->
    <div class="controls">
      <input v-model="start" placeholder="起点 ID (如 cnm_p001)" />
      <input v-model="end"   placeholder="终点 ID (如 cnm_p005)" />
      <button @click="loadSubgraph" :disabled="loading">
        {{ loading ? '加载中...' : '查询子图' }}
      </button>
    </div>
    <div v-if="error" class="error">⚠️ {{ error }}</div>

    <!-- 左侧详情 + 右侧图谱（flex 左右布局，占满 h1 下方空白） -->
    <div class="main-layout">
      <!-- 左侧：详情面板 -->
      <div class="detail-column">
        <div v-if="topicDetail" class="detail-panel">
          <h3>{{ topicDetail.chapter }}</h3>
          <div class="detail-meta">
            <span><strong>领域:</strong> {{ topicDetail.domin }}</span>
            <span><strong>学期:</strong> {{ topicDetail.grade_semester }}</span>
          </div>
          <div class="detail-section">
            <strong>描述:</strong> {{ topicDetail.description }}
          </div>
          <div class="detail-section">
            <strong>掌握标准:</strong>
            <ul>
              <li v-for="(c, i) in topicDetail.mastery_criteria.split(';')" :key="i">{{ c }}</li>
            </ul>
          </div>
          <div class="detail-section">
            <strong>相关题目:</strong>
            <ul>
              <li v-for="(q, i) in topicDetail.questions.split(';')" :key="i">{{ q }}</li>
            </ul>
          </div>
        </div>
        <div v-else class="detail-placeholder">
          👈 点击右侧图谱中的节点查看详情
        </div>
      </div>

      <!-- 右侧：图谱 -->
      <div class="graph-column">
        <div ref="cyContainer" class="cy-box"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import cytoscape from 'cytoscape'
import dagre from 'cytoscape-dagre'
import axios from 'axios'

cytoscape.use(dagre)

const start = ref('cnm_p001')
const end   = ref('cnm_p002')
const loading = ref(false)
const error = ref('')
const cyContainer = ref(null)
const topicDetail = ref(null)
let cy = null

// 复用同一个 ctx，避免每次点击/查询都新建 canvas
const measureCtx = document.createElement('canvas').getContext('2d')

function calcNodeSize(label, fontSize = 12, padding = 16) {
  measureCtx.font = `${fontSize}px "Microsoft YaHei", "PingFang SC", sans-serif`
  const textWidth = measureCtx.measureText(label).width
  const width = Math.ceil(Math.max(textWidth, 60)) + padding
  const height = fontSize + padding
  return { width, height }
}

async function loadSubgraph() {
  loading.value = true
  error.value = ''
  topicDetail.value = null
  try {
    const res = await axios.get('/api/graph', {
      params: { start: start.value, end: end.value }
    })

    if (res.data.error) {
      error.value = res.data.error
      return
    }

    const { nodes, edges } = res.data
    const processedNodes = nodes.map(node => {
      const { width, height } = calcNodeSize(node.data.label)
      return { ...node, data: { ...node.data, width, height } }
    })

    if (cy) cy.destroy()

    cy = cytoscape({
      container: cyContainer.value,
      elements: { nodes: processedNodes, edges },
      style: [
        {
          selector: 'node',
          style: {
            'label': 'data(label)',
            'text-valign': 'center',
            'text-wrap': 'wrap',
            'background-color': '#4a90e2',
            'color': '#fff',
            'font-size': 12,
            'shape': 'roundrectangle',
            'border-width': 1,
            'border-color': '#4a90e2',
            'width':  'data(width)',
            'height': 'data(height)'
          }
        },
        {
          selector: 'edge',
          style: {
            'width': 2,
            'line-color': '#9cc3e8',
            'target-arrow-color': '#9cc3e8',
            'target-arrow-shape': 'triangle',
            'curve-style': 'bezier'
          }
        }
      ],
      layout: { name: 'dagre', rankDir: 'TB', nodeSep: 60, rankSep: 100 }
    })

    cy.on('tap', 'node', async evt => {
      const nodeId = evt.target.data('id')
      try {
        const res = await axios.post('/api/topics', { id: nodeId })
        const { data: detail } = res.data
        topicDetail.value = detail
      } catch (err) {
        console.log(err)
      }
    })
  } catch (err) {
    error.value = err.response?.data?.detail || err.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  nextTick(loadSubgraph)
})
</script>

<style scoped>
.graph-wrapper { width: 100%; padding: 0 0 20px; box-sizing: border-box; }
.controls { margin-bottom: 12px; display: flex; gap: 8px; align-items: center; }
.controls input {
  padding: 7px 12px;
  border: 1px solid #d9e8f7;
  border-radius: 6px;
  background: #fff;
  color: #1f1f1f;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.controls input:focus {
  border-color: #4a90e2;
  box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.15);
}
.controls button {
  padding: 7px 18px;
  cursor: pointer;
  background: #4a90e2;
  color: #fff;
  border: none;
  border-radius: 6px;
  transition: background 0.2s;
}
.controls button:hover:not(:disabled) { background: #3b7dd8; }
.controls button:disabled { background: #c9d8e8; cursor: not-allowed; }
.error {
  background: #fff1f0;
  color: #c0392b;
  border: 1px solid #f5c2bd;
  padding: 8px 12px;
  border-radius: 6px;
  margin-bottom: 12px;
}

/* 左右布局：详情在左，图谱在右 */
.main-layout {
  display: flex;
  gap: 20px;
  align-items: stretch;
}
.detail-column {
  flex: 1;
  min-width: 280px;
  max-width: 420px;
}
.graph-column {
  flex: 2;
  min-width: 0;
}

/* 详情面板 */
.detail-panel {
  padding: 20px;
  border: 1px solid #d9e8f7;
  border-radius: 8px;
  font-size: 14px;
  background: #fff;
  height: 100%;
  box-sizing: border-box;
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.06);
}
.detail-placeholder {
  padding: 40px 20px;
  border: 2px dashed #cfe1f5;
  border-radius: 8px;
  color: #7b8fa3;
  background: #fbfdff;
  text-align: center;
  font-size: 14px;
}
.detail-panel h3 {
  margin-top: 0;
  margin-bottom: 16px;
  color: #111111;
  font-size: 18px;
  border-bottom: 2px solid #4a90e2;
  padding-bottom: 10px;
}
.detail-meta { margin-bottom: 16px; color: #5a6b7b; font-size: 13px; }
.detail-meta span { display: block; margin-bottom: 4px; }
.detail-section { margin-bottom: 14px; line-height: 1.6; font-size: 13px; }
.detail-section strong { color: #111111; display: block; margin-bottom: 4px; }
.detail-panel ul { padding-left: 20px; margin: 4px 0; }
.detail-panel li { margin-bottom: 4px; line-height: 1.5; font-size: 13px; }

/* 图谱 */
.cy-box {
  width: 100%;
  height: 600px;
  border: 1px solid #d9e8f7;
  border-radius: 8px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(74, 144, 226, 0.06);
}
</style>
