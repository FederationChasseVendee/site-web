import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";

const linkSchema = z.object({
  label: z.string(),
  url: z.string(),
});

const pages = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/pages" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    eyebrow: z.string().default("La Fédération"),
    intro: z.string(),
    showInNavigation: z.boolean().default(true),
    navigationLabel: z.string().optional(),
    navigationOrder: z.number().int().default(100),
    cards: z.array(z.object({
      icon: z.enum(["pin", "phone", "mail", "learn", "training"]).default("learn"),
      label: z.string(),
      title: z.string(),
      lines: z.array(z.string()).default([]),
      link: linkSchema.optional(),
    })).default([]),
    schedule: z.object({
      eyebrow: z.string(),
      title: z.string(),
      rows: z.array(z.object({
        label: z.string(),
        value: z.string(),
      })).default([]),
      note: z.string().optional(),
    }).optional(),
    callout: z.object({
      eyebrow: z.string(),
      title: z.string(),
      text: z.string(),
      action: linkSchema,
    }).optional(),
  }),
});

export const collections = { pages };
