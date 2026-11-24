<template>
  <h1 id="title">中小学校知识考点可视化图谱</h1>
  <GraphView />
</template>

<script setup>
import GraphView from './components/GraphView.vue'
</script>

<style>
#title {
  text-align: center;
  color: #111111;
  font-size: 26px;
  font-weight: 600;
  letter-spacing: 1px;
  padding-bottom: 16px;
  margin-bottom: 20px;
  border-bottom: 2px solid #d9e8f7;
}
</style>