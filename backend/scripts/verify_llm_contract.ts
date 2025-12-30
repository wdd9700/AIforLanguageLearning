
import { PromptManager } from '../src/managers/prompt-manager';
import { createLogger } from '../src/utils/logger';

// --- Frontend Interfaces (Copied for Validation) ---

// 1. Analysis Interface
interface AnalysisResult {
  dimension: string;
  score: number;
  trend: number;
  insights: string[];
  recommendations: string[];
  visualization: {
    type: 'radar' | 'line' | 'bar';
    title: string;
    labels: string[];
    datasets: Array<{
      label: string;
      data: number[];
    }>;
  };
}

// 2. Essay Interface
interface EssayScore {
  vocabulary: number;
  grammar: number;
  fluency: number;
  logic: number;
  content: number;
  structure: number;
  total: number;
}

interface EssayCorrectionResult {
  scores: EssayScore;
  feedback: string;
  correction: string;
  suggestions?: string[];
  questions?: string[];
  improvements?: string[];
  evaluation?: string;
}

// --- Validation Logic ---

const logger = createLogger('ContractVerifier');
const promptManager = new PromptManager();

async function verifyAnalysisContract() {
  console.log('\n--- Verifying Learning Analysis Contract ---');
  
  // 1. Render Prompt
  const prompt = await promptManager.render('analysis/learning_report', {
    dimension: 'Overall',
    recordsSummary: 'Vocabulary: Learned "apple", "banana". Essay: Wrote about summer vacation.'
  });
  
  console.log('Generated Prompt Preview:\n', prompt.substring(0, 200) + '...');

  // 2. Simulate LLM Response (Based on Prompt Instructions)
  const mockLlmResponse = `{
    "score": 85,
    "trend": 1,
    "insights": ["Strong vocabulary", "Needs grammar practice"],
    "recommendations": ["Read more news"],
    "visualization": {
      "type": "radar",
      "title": "Overall Competence",
      "labels": ["Vocabulary", "Grammar", "Listening", "Speaking", "Reading", "Writing"],
      "datasets": [
        {
          "label": "Current Level",
          "data": [80, 70, 85, 60, 75, 70]
        }
      ]
    }
  }`;

  // 3. Validate
  try {
    const data = JSON.parse(mockLlmResponse);
    const result: AnalysisResult = {
      dimension: 'Overall',
      ...data
    };
    
    // Type Check (Runtime)
    if (result.visualization.type !== 'radar') throw new Error('Invalid chart type');
    if (!Array.isArray(result.visualization.datasets)) throw new Error('Missing datasets');
    
    console.log('✅ Analysis Contract Validated: JSON matches Frontend Interface');
  } catch (e) {
    console.error('❌ Analysis Contract Failed:', e);
  }
}

async function verifyEssayContract() {
  console.log('\n--- Verifying Essay Correction Contract ---');

  // 1. Render Prompt
  const prompt = await promptManager.render('essay/correction', {
    language: 'English',
    text: 'I go to school yesterday.'
  });

  console.log('Generated Prompt Preview:\n', prompt.substring(0, 200) + '...');

  // 2. Simulate LLM Response
  const mockLlmResponse = `{
    "scores": {
      "vocabulary": 70,
      "grammar": 60,
      "fluency": 75,
      "logic": 80,
      "content": 85,
      "structure": 75,
      "total": 74
    },
    "feedback": "Good effort, but watch your tense.",
    "correction": "I went to school yesterday.",
    "suggestions": ["Review past tense verbs"],
    "questions": ["Did you mean yesterday or today?"],
    "improvements": ["Use 'went' instead of 'go'"],
    "evaluation": "The student shows basic understanding..."
  }`;

  // 3. Validate
  try {
    const data = JSON.parse(mockLlmResponse);
    const result: EssayCorrectionResult = data;

    if (typeof result.scores.total !== 'number') throw new Error('Missing total score');
    if (typeof result.correction !== 'string') throw new Error('Missing correction');

    console.log('✅ Essay Contract Validated: JSON matches Frontend Interface');
  } catch (e) {
    console.error('❌ Essay Contract Failed:', e);
  }
}

async function verifyVoicePromptContract() {
  console.log('\n--- Verifying Voice Prompt Expansion Contract ---');

  // 1. Render Prompt
  const prompt = await promptManager.render('analysis/prompt_expansion', {
    scenario: 'Ordering coffee',
    targetLang: 'English'
  });

  console.log('Generated Prompt Preview:\n', prompt.substring(0, 200) + '...');
  
  // Voice prompt output is just text, so validation is simpler
  if (prompt.includes('Ordering coffee') && prompt.includes('English')) {
      console.log('✅ Voice Prompt Contract Validated: Template substitution works');
  } else {
      console.error('❌ Voice Prompt Contract Failed: Template substitution failed');
  }
}

async function run() {
  await verifyAnalysisContract();
  await verifyEssayContract();
  await verifyVoicePromptContract();
}

run().catch(console.error);
