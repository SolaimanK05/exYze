// Footprints (metres) of the furniture used by the sample plan.
// Placeholder until the real catalogue is served by GET /api/catalog (Package B).

export interface Footprint {
  name: string
  width: number
  depth: number
}

export const placeholderCatalog: Record<string, Footprint> = {
  bed_double: { name: 'Double bed', width: 1.6, depth: 2.0 },
  sofa_3: { name: 'Three-seat sofa', width: 2.0, depth: 0.9 },
  tv_unit: { name: 'TV unit', width: 1.5, depth: 0.4 },
  dining_table_4: { name: 'Dining table', width: 1.4, depth: 0.9 },
  kitchen_counter: { name: 'Kitchen counter', width: 2.4, depth: 0.6 },
  fridge: { name: 'Fridge', width: 0.7, depth: 0.7 },
  wardrobe: { name: 'Wardrobe', width: 1.2, depth: 0.6 },
  toilet: { name: 'Toilet', width: 0.4, depth: 0.7 },
  basin: { name: 'Basin', width: 0.6, depth: 0.45 },
  shower_tray: { name: 'Shower tray', width: 0.9, depth: 0.9 },
}

/** Used for any catalogue code that is not in the list above. */
export const unknownFootprint: Footprint = { name: 'Item', width: 0.6, depth: 0.6 }

export function footprintFor(code: string): Footprint {
  return placeholderCatalog[code] ?? unknownFootprint
}
