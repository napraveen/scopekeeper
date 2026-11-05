import type { Category } from '@/lib/api/types'
import { Bug, CircleCheck, CircleHelp, CircleSlash, Copy, Gavel, type LucideIcon } from 'lucide-react'

export interface CategoryMeta {
  label: string
  short: string
  icon: LucideIcon
  /** Tailwind classes using the category tokens (fg, bg, ring). */
  className: string
  /** Solid colour for bars. */
  barClass: string
  hint: string
}

export const CATEGORY: Record<Category, CategoryMeta> = {
  DEFECT: {
    label: 'Defect',
    short: 'Defect',
    icon: Bug,
    className: 'text-cat-defect bg-cat-defect-bg ring-cat-defect/25',
    barClass: 'bg-cat-defect',
    hint: 'Broken against the contract. Always free.',
  },
  IN_SCOPE: {
    label: 'In scope',
    short: 'In scope',
    icon: CircleCheck,
    className: 'text-cat-in-scope bg-cat-in-scope-bg ring-cat-in-scope/25',
    barClass: 'bg-cat-in-scope',
    hint: 'Covered by the signed scope of work.',
  },
  UNCLEAR: {
    label: 'Unclear',
    short: 'Unclear',
    icon: CircleHelp,
    className: 'text-cat-unclear bg-cat-unclear-bg ring-cat-unclear/25',
    barClass: 'bg-cat-unclear',
    hint: 'Needs one question to the client before it can be sorted.',
  },
  OUT_OF_SCOPE: {
    label: 'Out of scope',
    short: 'Out of scope',
    icon: CircleSlash,
    className: 'text-cat-out bg-cat-out-bg ring-cat-out/25',
    barClass: 'bg-cat-out',
    hint: 'Not in the contract. Opens a change request.',
  },
  DUPLICATE: {
    label: 'Duplicate',
    short: 'Duplicate',
    icon: Copy,
    className: 'text-cat-duplicate bg-cat-duplicate-bg ring-cat-duplicate/25',
    barClass: 'bg-cat-duplicate',
    hint: 'Already asked; linked to the earlier ask.',
  },
  ALREADY_DECIDED: {
    label: 'Already decided',
    short: 'Decided',
    icon: Gavel,
    className: 'text-cat-decided bg-cat-decided-bg ring-cat-decided/25',
    barClass: 'bg-cat-decided',
    hint: 'A past decision already answers this.',
  },
}

export const CATEGORY_ORDER: Category[] = ['DEFECT', 'IN_SCOPE', 'UNCLEAR', 'OUT_OF_SCOPE', 'DUPLICATE', 'ALREADY_DECIDED']
