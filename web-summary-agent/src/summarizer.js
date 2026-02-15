import { GoogleGenerativeAI } from '@google/generative-ai';

const MODEL_NAME = 'gemini-2.0-flash';

let genAI;
let model;

/** Initialize the Gemini client. Call once at startup. */
export function initSummarizer(apiKey) {
  genAI = new GoogleGenerativeAI(apiKey);
  model = genAI.getGenerativeModel({ model: MODEL_NAME });
}

/**
 * Summarize scraped page content using Gemini.
 *
 * @param {{ title: string, content: string, url: string, siteName: string }} pageData
 * @returns {Promise<string>} markdown-formatted summary
 */
export async function summarize(pageData) {
  if (!model) throw new Error('Summarizer not initialized – call initSummarizer() first');

  // Trim content to stay within token limits (~60k chars ≈ 15k tokens)
  const trimmedContent = pageData.content.slice(0, 60_000);

  const prompt = buildPrompt(pageData, trimmedContent);

  const result = await model.generateContent(prompt);
  const response = result.response;
  return response.text();
}

function buildPrompt(pageData, content) {
  return `You are a helpful web content summarizer. You will be given the text content of a web page that was scraped by a browser. Your job is to produce a clear, well-structured summary.

**Page Title:** ${pageData.title}
**Source:** ${pageData.siteName}
**URL:** ${pageData.url}

---

**Page Content:**
${content}

---

**Instructions:**
1. Write a concise summary (3-6 paragraphs) that captures the key points.
2. If this is a discussion thread (Reddit, Hacker News), summarize the main post AND the most interesting/insightful comments, noting areas of agreement and disagreement.
3. If this is an article (Substack, Medium, blog), summarize the thesis, key arguments, supporting evidence, and conclusion.
4. If this is a code repository (GitHub), describe what the project does, its tech stack, and notable features.
5. Use bullet points for lists of takeaways when appropriate.
6. At the end, include a "Key Takeaways" section with 3-5 bullet points.
7. Keep the tone neutral and informative.
8. Format the output in Discord-friendly markdown (use **bold**, *italic*, bullet points). Do NOT use headings larger than ## since Discord doesn't render them well.
9. Keep the total summary under 1800 characters so it fits in a single Discord message.`;
}
