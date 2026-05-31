<script setup lang="ts">
import FormField from "./FormField.vue";
import PanelHeading from "./PanelHeading.vue";

const props = withDefaults(
  defineProps<{
    feedbackMessage?: string | null;
    errorMessage?: string | null;
    patchText: string;
    replaceText: string;
    deleting?: boolean;
    patchFieldLabel?: string;
    replaceFieldLabel?: string;
    patchButtonLabel?: string;
    replaceButtonLabel?: string;
    deleteButtonLabel?: string;
    deletingButtonLabel?: string;
  }>(),
  {
    feedbackMessage: null,
    errorMessage: null,
    deleting: false,
    patchFieldLabel: "Fields to update",
    replaceFieldLabel: "Full record",
    patchButtonLabel: "Save changes",
    replaceButtonLabel: "Replace",
    deleteButtonLabel: "Delete",
    deletingButtonLabel: "Deleting...",
  },
);

defineEmits<{
  patch: [];
  replace: [];
  delete: [];
  'update:patchText': [value: string];
  'update:replaceText': [value: string];
}>();
</script>

<template>
  <article class="panel panel-stack">
    <PanelHeading eyebrow="Edit" title="Update or delete" />

    <p v-if="feedbackMessage" class="feedback">{{ feedbackMessage }}</p>
    <p v-if="errorMessage" class="feedback error-copy">{{ errorMessage }}</p>

    <FormField class="form-field--wide" :label="patchFieldLabel">
      <textarea
        class="text-area"
        spellcheck="false"
        :value="patchText"
        @input="$emit('update:patchText', ($event.target as HTMLTextAreaElement).value)"
      />
    </FormField>

    <div class="button-row">
      <button type="button" class="button" @click="$emit('patch')">{{ patchButtonLabel }}</button>
    </div>

    <FormField class="form-field--wide" :label="replaceFieldLabel">
      <textarea
        class="text-area"
        spellcheck="false"
        :value="replaceText"
        @input="$emit('update:replaceText', ($event.target as HTMLTextAreaElement).value)"
      />
    </FormField>

    <div class="button-row">
      <button type="button" class="button button--accent" @click="$emit('replace')">{{ replaceButtonLabel }}</button>
      <button type="button" class="button button--danger" :disabled="deleting" @click="$emit('delete')">
        {{ deleting ? deletingButtonLabel : deleteButtonLabel }}
      </button>
    </div>
  </article>
</template>