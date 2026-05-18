<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { summarizeBuildOrder, summarizeOpening } from "../build-orders";
import type { ReplayBuildOrderEntry } from "../types";

const props = defineProps<{
  entries?: ReplayBuildOrderEntry[] | null;
  playerName: string;
}>();

const expanded = ref(false);
const defaultVisibleStepCount = 24;
const displaySteps = computed(() => summarizeBuildOrder(props.entries));
const opener = computed(() => summarizeOpening(props.entries));
const hasOverflow = computed(() => displaySteps.value.length > defaultVisibleStepCount);
const visibleSteps = computed(() => {
  if (expanded.value || !hasOverflow.value) {
    return displaySteps.value;
  }
  return displaySteps.value.slice(0, defaultVisibleStepCount);
});

watch(
  () => props.entries,
  () => {
    expanded.value = false;
  },
);
</script>

<template>
  <section class="build-order-block">
    <div class="build-order-block__header">
      <div class="build-order-block__heading">
        <strong class="build-order-block__title">Build order</strong>
      </div>
    </div>

    <p v-if="opener" class="build-order-block__summary">
      {{ opener }}
    </p>

    <p v-if="!displaySteps.length" class="muted-copy">
      No build order extracted for {{ playerName }}.
    </p>

    <div v-else class="build-order-sequence" role="table" :aria-label="`${playerName} build order`">
      <div class="build-order-sequence__head" role="row">
        <span class="build-order-sequence__heading" role="columnheader">Time</span>
        <span class="build-order-sequence__heading" role="columnheader">Supply</span>
        <span class="build-order-sequence__heading" role="columnheader">Build</span>
      </div>

      <li
        v-for="step in visibleSteps"
        :key="step.id"
        class="build-order-step"
        role="row"
      >
        <span class="build-order-step__time" role="cell">{{ step.time }}</span>
        <span class="build-order-step__supply" role="cell">{{ step.supply }}</span>
        <div class="build-order-step__build" role="cell">
          <strong class="build-order-step__label">{{ step.build }}</strong>
          <span v-if="step.isChronoboosted" class="tag build-order-step__badge">Chronoboost</span>
        </div>
      </li>
    </div>

    <div v-if="hasOverflow" class="build-order-block__footer">
      <button type="button" class="button button--ghost build-order-block__toggle" @click="expanded = !expanded">
        {{ expanded ? "Collapse sequence" : "Show full sequence" }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.build-order-block {
  position: relative;
  z-index: 3;
  display: grid;
  gap: 14px;
  min-width: 0;
}

.build-order-block__header {
  display: flex;
  align-items: start;
  justify-content: space-between;
  gap: 12px;
}

.build-order-block__heading {
  display: grid;
  gap: 4px;
}

.build-order-block__title {
  font-family: var(--display);
  font-size: 1rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.build-order-block__summary {
  margin: 0;
  color: var(--text-dim);
  line-height: 1.6;
}

.build-order-sequence {
  margin: 0;
  display: grid;
  gap: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.build-order-sequence__head {
  display: grid;
  grid-template-columns: 68px 56px minmax(0, 1fr);
  gap: 12px;
  padding: 10px 12px;
  background: linear-gradient(180deg, rgba(18, 27, 42, 0.97), rgba(10, 16, 26, 1));
  border-bottom: 1px solid var(--border);
}

.build-order-sequence__heading {
  color: var(--text-muted);
  font-family: var(--display);
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.build-order-block__footer {
  display: flex;
  justify-content: flex-end;
}

.build-order-block__toggle {
  min-height: 36px;
}

.build-order-step {
  display: grid;
  grid-template-columns: 68px 56px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 10px 12px;
  background: linear-gradient(180deg, rgba(15, 22, 34, 0.9), rgba(10, 16, 26, 0.96));
}

.build-order-step + .build-order-step {
  border-top: 1px solid var(--border-muted);
}

.build-order-step__time {
  display: inline-flex;
  align-items: center;
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 0.8rem;
}

.build-order-step__supply {
  color: var(--text);
  font-family: var(--mono);
  font-size: 0.85rem;
}

.build-order-step__build {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}

.build-order-step__label {
  font-weight: 600;
  line-height: 1.35;
}

.build-order-step__badge {
  border-color: rgba(217, 171, 55, 0.28);
  background: var(--amber-wash);
  color: var(--amber-strong);
}

@media (max-width: 640px) {
  .build-order-sequence__head,
  .build-order-step {
    grid-template-columns: 60px 48px minmax(0, 1fr);
    gap: 6px;
  }
}
</style>