<template>
  <div ref="host" style="height: 320px"></div>
</template>

<script setup lang="ts">
import * as echarts from "echarts";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

const props = defineProps<{ items: { name: string; score: number }[] }>();
const host = ref<HTMLDivElement>();
let chart: echarts.ECharts | null = null;

function render() {
  if (!host.value) return;
  chart = chart || echarts.init(host.value);
  chart.setOption({
    radar: {
      indicator: props.items.map((item) => ({ name: item.name, max: 100 })),
      radius: 100,
      axisName: { color: "#6f6f6c", fontFamily: "IBM Plex Sans SC, PingFang SC, sans-serif", fontSize: 12 },
      axisLine: { lineStyle: { color: "#e7e7e4" } },
      splitLine: { lineStyle: { color: "#e7e7e4" } },
      splitArea: { areaStyle: { color: ["#ffffff", "#f6f6f4"] } },
    },
    series: [
      {
        type: "radar",
        symbol: "circle",
        symbolSize: 5,
        data: [{ value: props.items.map((item) => item.score), name: "评分", areaStyle: { color: "rgba(216, 74, 50, 0.12)" } }],
        lineStyle: { color: "#161616", width: 1.5 },
        itemStyle: { color: "#d84a32" },
      },
    ],
  });
}

onMounted(render);
watch(() => props.items, render, { deep: true });
onBeforeUnmount(() => chart?.dispose());
</script>
