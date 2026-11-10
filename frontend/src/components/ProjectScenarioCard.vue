<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Spinner } from '@/components/ui/spinner'
import {
  FlaskConical,
  Sparkles,
  CheckCircle2,
  Plus,
  Trash2,
  ChevronDown,
  ChevronUp,
  Save,
  ShieldAlert,
} from '@lucide/vue'

export interface ScenarioCategoryItem {
  name: string
  dose?: string
  color: string
  is_control?: boolean
}

export interface ScenarioData {
  type: string
  title: string
  target: string
  target_label: string
  categories: ScenarioCategoryItem[]
}

const props = withDefaults(
  defineProps<{
    projectId?: string
    projectName?: string
    initialScenario?: ScenarioData | null
    fileNames?: string[]
    projectProgress?: number
  }>(),
  {
    initialScenario: null,
    fileNames: () => [],
    projectProgress: 0,
  }
)

const emit = defineEmits<{
  (e: 'update:scenario', scenario: ScenarioData): void
  (e: 'saved', scenario: ScenarioData): void
}>()

// 高對比識別調色盤
const PALETTE = [
  '#64748b', // 對照組灰色 (Slate)
  '#10b981', // 翡翠綠 (Emerald)
  '#8b5cf6', // 紫羅蘭 (Violet)
  '#f59e0b', // 琥珀黃 (Amber)
  '#0ea5e9', // 天空藍 (Sky)
  '#ec4899', // 亮粉紅 (Pink)
  '#f97316', // 活力橘 (Orange)
  '#06b6d4', // 湖水青 (Cyan)
  '#84cc16', // 萊姆綠 (Lime)
  '#e11d48', // 玫瑰紅 (Rose)
]

const isOpen = ref(true)
const isSaving = ref(false)
const isSaved = ref(false)
const isDirty = ref(false)

const scenarioType = ref('pesticide')
const targetName = ref('')
const categories = ref<ScenarioCategoryItem[]>([])

const targetLabel = computed(() => {
  if (scenarioType.value === 'pesticide') return '農藥名稱'
  if (scenarioType.value === 'fertilizer') return '肥料品項'
  if (scenarioType.value === 'variety') return '試驗作物品種'
  return '試驗處理標的名稱'
})

const scenarioTitle = computed(() => {
  if (scenarioType.value === 'pesticide') return '農藥藥效試驗'
  if (scenarioType.value === 'fertilizer') return '肥料肥力試驗'
  if (scenarioType.value === 'variety') return '品種篩選試驗'
  return '自訂試驗情境'
})

// 初始化農藥情境預設分類
function initDefaultPesticide(target = '快得寧') {
  scenarioType.value = 'pesticide'
  targetName.value = target
  categories.value = [
    { name: '未施藥對照 (CK)', dose: '', color: PALETTE[0], is_control: true },
    { name: '500x', dose: '500x', color: PALETTE[1], is_control: false },
    { name: '1000x', dose: '1000x', color: PALETTE[2], is_control: false },
    { name: '2000x', dose: '2000x', color: PALETTE[3], is_control: false },
  ]
  isDirty.value = true
}

// 初始化肥料情境預設分類
function initDefaultFertilizer(target = '特肥一號') {
  scenarioType.value = 'fertilizer'
  targetName.value = target
  categories.value = [
    { name: '不施肥對照 (CK)', dose: '', color: PALETTE[0], is_control: true },
    { name: '減量組 (50%)', dose: '50%', color: PALETTE[4], is_control: false },
    { name: '標準量 (100%)', dose: '100%', color: PALETTE[1], is_control: false },
    { name: '倍量組 (200%)', dose: '200%', color: PALETTE[2], is_control: false },
  ]
  isDirty.value = true
}

// 自訂情境預設分類
function initDefaultCustom() {
  scenarioType.value = 'custom'
  targetName.value = '處理品項'
  categories.value = [
    { name: '對照組 (CK)', dose: '', color: PALETTE[0], is_control: true },
    { name: '處理組 A', dose: '組別 A', color: PALETTE[1], is_control: false },
    { name: '處理組 B', dose: '組別 B', color: PALETTE[2], is_control: false },
  ]
  isDirty.value = true
}

// 根據專案名稱與檔案清單進行 AI 語意推估
const aiInferenceSuggestion = computed<{ type: string; target: string; reason: string } | null>(() => {
  const combined = `${props.projectName || ''} ${(props.fileNames || []).join(' ')}`.toLowerCase()
  if (
    combined.includes('農藥') ||
    combined.includes('藥') ||
    combined.includes('快得寧') ||
    combined.includes('500x') ||
    combined.includes('1000x') ||
    combined.includes('pesticide')
  ) {
    let guessedName = '快得寧'
    if (combined.includes('快得寧')) guessedName = '快得寧'
    else if (combined.includes('得寧')) guessedName = '得寧'
    return {
      type: 'pesticide',
      target: guessedName,
      reason: '偵測到檔名或專案包含農藥/稀釋倍數關鍵字',
    }
  }
  if (combined.includes('肥') || combined.includes('fertilizer')) {
    return {
      type: 'fertilizer',
      target: '特肥一號',
      reason: '偵測到檔名或專案包含肥料試驗關鍵字',
    }
  }
  return null
})

// 套用 AI 推估
function applyAiSuggestion() {
  if (!aiInferenceSuggestion.value) return
  if (aiInferenceSuggestion.value.type === 'pesticide') {
    initDefaultPesticide(aiInferenceSuggestion.value.target)
  } else if (aiInferenceSuggestion.value.type === 'fertilizer') {
    initDefaultFertilizer(aiInferenceSuggestion.value.target)
  }
}

// 新增分類項目
function addCategory() {
  const nextColorIdx = (categories.value.length % (PALETTE.length - 1)) + 1
  categories.value.push({
    name: `劑量組 ${categories.value.length}`,
    dose: '',
    color: PALETTE[nextColorIdx],
    is_control: false,
  })
  isDirty.value = true
}

// 刪除分類項目
function removeCategory(index: number) {
  categories.value.splice(index, 1)
  isDirty.value = true
}

// 載入已存在的 Scenario 資料
function loadFromScenario(data: ScenarioData) {
  if (!data) return
  scenarioType.value = data.type || 'pesticide'
  targetName.value = data.target || ''
  categories.value = (data.categories || []).map((c) => ({
    name: c.name,
    dose: c.dose || c.name,
    color: c.color || PALETTE[1],
    is_control: c.is_control ?? false,
  }))
  isDirty.value = false
  isSaved.value = true
}

// 監聽傳入的 initialScenario
watch(
  () => props.initialScenario,
  (newScenario) => {
    if (newScenario && typeof newScenario === 'object' && Object.keys(newScenario).length > 0) {
      loadFromScenario(newScenario as ScenarioData)
      // 若已完成 100% 且已有設定，預設收合以節省空間
      if (props.projectProgress === 100) {
        isOpen.value = false
      }
    } else {
      // 專案尚未設定情境，預設提供標準農藥試驗模板供手動配置
      initDefaultPesticide()
      isOpen.value = true
    }
  },
  { immediate: true }
)

// 儲存情境特徵至後端資料庫
async function handleSave() {
  if (!props.projectId || props.projectId === 'home') return

  const payload: ScenarioData = {
    type: scenarioType.value,
    title: scenarioTitle.value,
    target: targetName.value.trim(),
    target_label: targetLabel.value,
    categories: categories.value.map((c) => ({
      name: c.name.trim(),
      dose: (c.dose || c.name).trim(),
      color: c.color,
      is_control: c.is_control ?? false,
    })),
  }

  isSaving.value = true
  try {
    const res = await fetch(`/api/task/scenario/${props.projectId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: payload }),
    })
    const data = await res.json().catch(() => null)
    if (res.ok && data?.result) {
      isDirty.value = false
      isSaved.value = true
      emit('update:scenario', payload)
      emit('saved', payload)
    } else {
      alert(data?.message || '儲存情境特徵失敗')
    }
  } catch (err) {
    console.error('儲存情境特徵錯誤:', err)
    alert('網路連線失敗，請稍後再試')
  } finally {
    isSaving.value = false
  }
}
</script>

<template>
  <Card class="border shadow-sm transition-all duration-200">
    <Collapsible v-model:open="isOpen">
      <CardHeader class="py-3 px-5">
        <div class="flex items-center justify-between gap-3">
          <div class="flex flex-wrap items-center gap-2">
            <div class="flex items-center gap-1.5 font-semibold text-base text-foreground">
              <FlaskConical class="size-4 text-primary" />
              <span>專案試驗情境特徵</span>
            </div>

            <!-- 折疊時的摘要預覽徽章 -->
            <template v-if="!isOpen">
              <Badge v-if="targetName" variant="secondary" class="font-normal text-xs">
                {{ targetLabel }}: <strong class="ml-1 text-foreground">{{ targetName }}</strong>
              </Badge>
              <div class="flex items-center gap-1">
                <Badge
                  v-for="(cat, idx) in categories.slice(0, 4)"
                  :key="idx"
                  variant="outline"
                  class="text-[11px] font-normal py-0 px-1.5 flex items-center gap-1"
                >
                  <span class="size-1.5 rounded-full shrink-0" :style="{ backgroundColor: cat.color }" />
                  {{ cat.name }}
                </Badge>
                <span v-if="categories.length > 4" class="text-[10px] text-muted-foreground">
                  +{{ categories.length - 4 }}
                </span>
              </div>
            </template>

            <!-- 狀態提示 -->
            <Badge v-if="isSaved && !isDirty" variant="outline" class="text-emerald-600 border-emerald-500/30 bg-emerald-50/50 text-[11px] py-0">
              <CheckCircle2 class="size-3 mr-1" />
              已儲存特徵
            </Badge>
            <Badge v-else-if="isDirty" variant="outline" class="text-amber-600 border-amber-500/30 bg-amber-50/50 text-[11px] py-0">
              未儲存變更
            </Badge>
          </div>

          <div class="flex items-center gap-2">
            <!-- 展開 / 收合開關 -->
            <CollapsibleTrigger as-child>
              <Button size="sm" variant="ghost" class="h-7 px-2 text-xs gap-1 text-muted-foreground hover:text-foreground">
                <span>{{ isOpen ? '收合' : '展開編輯' }}</span>
                <ChevronUp v-if="isOpen" class="size-3.5" />
                <ChevronDown v-else class="size-3.5" />
              </Button>
            </CollapsibleTrigger>
          </div>
        </div>

        <CardDescription v-if="isOpen" class="text-xs pt-1">
          設定本試驗之處理標的與分組劑量。儲存後將作為此專案的資料特徵，並自動帶入下方小區標註作為預設標籤與顏色。
        </CardDescription>
      </CardHeader>

      <CollapsibleContent>
        <CardContent class="pt-0 pb-4 px-5 space-y-4">
          <!-- 1. 情境範本切換 -->
          <div class="flex flex-wrap items-center justify-between gap-3 border-t pt-3">
            <div class="flex items-center gap-2">
              <Label class="text-xs text-muted-foreground font-medium">試驗情境：</Label>
              <div class="flex gap-1.5">
                <Button
                  size="sm"
                  type="button"
                  :variant="scenarioType === 'pesticide' ? 'default' : 'outline'"
                  class="h-7 text-xs px-2.5"
                  @click="initDefaultPesticide()"
                >
                  農藥藥效試驗
                </Button>
                <Button
                  size="sm"
                  type="button"
                  :variant="scenarioType === 'fertilizer' ? 'default' : 'outline'"
                  class="h-7 text-xs px-2.5"
                  @click="initDefaultFertilizer()"
                >
                  肥料肥力試驗
                </Button>
                <Button
                  size="sm"
                  type="button"
                  :variant="scenarioType === 'custom' ? 'default' : 'outline'"
                  class="h-7 text-xs px-2.5"
                  @click="initDefaultCustom()"
                >
                  自訂試驗
                </Button>
              </div>
            </div>

            <!-- 標的名稱輸入 -->
            <div class="flex items-center gap-2">
              <Label for="target-input" class="text-xs text-muted-foreground font-medium whitespace-nowrap">
                {{ targetLabel }}：
              </Label>
              <Input
                id="target-input"
                v-model="targetName"
                placeholder="例如: 快得寧"
                class="h-7 w-40 text-xs"
                @input="isDirty = true"
                @keydown.enter.prevent="handleSave"
              />
            </div>
          </div>

          <!-- 2. 動態劑量/處理組清單 -->
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <Label class="text-xs font-semibold text-foreground flex items-center gap-1.5">
                <span>試驗組別與分類色彩標籤</span>
                <span class="text-[11px] font-normal text-muted-foreground">（不同分類標記不同顏色）</span>
              </Label>
              <Button
                size="sm"
                variant="outline"
                type="button"
                class="h-6 text-xs px-2 gap-1"
                @click="addCategory"
              >
                <Plus class="size-3" />
                新增組別
              </Button>
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-2.5">
              <div
                v-for="(cat, idx) in categories"
                :key="idx"
                class="flex flex-col gap-1.5 p-2 rounded-lg border bg-card/60 relative group hover:border-primary/40 transition-colors"
              >
                <!-- 頂部顏色與刪除按鈕 -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-1.5">
                    <input
                      v-model="cat.color"
                      type="color"
                      aria-label="選擇組別代表顏色"
                      class="size-4 rounded cursor-pointer border-0 p-0 bg-transparent"
                      @input="isDirty = true"
                    />
                    <Badge
                      :variant="cat.is_control ? 'secondary' : 'outline'"
                      class="text-[10px] py-0 px-1 font-mono cursor-pointer"
                      :style="!cat.is_control ? { borderColor: cat.color + '80', color: cat.color } : {}"
                      @click="cat.is_control = !cat.is_control; isDirty = true"
                    >
                      {{ cat.is_control ? '對照組 (CK)' : '處理組' }}
                    </Badge>
                  </div>

                  <button
                    v-if="categories.length > 1"
                    type="button"
                    aria-label="移除此組別"
                    class="text-muted-foreground hover:text-destructive opacity-70 group-hover:opacity-100 transition-opacity p-0.5 rounded cursor-pointer"
                    @click="removeCategory(idx)"
                  >
                    <Trash2 class="size-3.5" />
                  </button>
                </div>

                <!-- 名稱與劑量輸入 -->
                <div class="space-y-1">
                  <Input
                    v-model="cat.name"
                    placeholder="組別名稱 (如: 500x)"
                    class="h-6 text-xs px-1.5 font-medium"
                    @input="isDirty = true"
                    @keydown.enter.prevent="handleSave"
                  />
                  <Input
                    v-if="!cat.is_control"
                    v-model="cat.dose"
                    placeholder="備註劑量 (選填)"
                    class="h-5 text-[11px] px-1.5 text-muted-foreground"
                    @input="isDirty = true"
                    @keydown.enter.prevent="handleSave"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- 3. 操作按鈕列 -->
          <div class="flex items-center justify-between pt-1 border-t">
            <div class="text-[11px] text-muted-foreground flex items-center gap-1">
              <ShieldAlert class="size-3.5 text-muted-foreground/70" />
              <span>按 Enter 或點擊右側按鈕儲存專案特徵</span>
            </div>

            <Button
              data-tour="save-scenario"
              size="sm"
              class="h-7 text-xs gap-1.5 px-3 cursor-pointer"
              :disabled="isSaving"
              @click="handleSave"
            >
              <Spinner v-if="isSaving" class="size-3.5 animate-spin" />
              <Save v-else class="size-3.5" />
              <span>{{ isSaving ? '儲存中...' : '儲存情境特徵' }}</span>
            </Button>
          </div>
        </CardContent>
      </CollapsibleContent>
    </Collapsible>
  </Card>
</template>
