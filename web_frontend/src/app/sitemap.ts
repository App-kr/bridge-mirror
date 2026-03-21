import type { MetadataRoute } from 'next'

const BASE = 'https://bridgejob.co.kr'

export default function sitemap(): MetadataRoute.Sitemap {
  const boards = ['korea', 'visa', 'support', 'support_kr', 'tips', 'testimonials']

  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: new Date(), changeFrequency: 'weekly', priority: 1.0 },
    { url: `${BASE}/jobs`, lastModified: new Date(), changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/apply`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE}/inquiry`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE}/community`, lastModified: new Date(), changeFrequency: 'weekly', priority: 0.7 },
    { url: `${BASE}/about`, lastModified: new Date(), changeFrequency: 'monthly', priority: 0.7 },
  ]

  const boardPages: MetadataRoute.Sitemap = boards.map((b) => ({
    url: `${BASE}/community/${b}`,
    lastModified: new Date(),
    changeFrequency: 'weekly' as const,
    priority: 0.6,
  }))

  return [...staticPages, ...boardPages]
}
