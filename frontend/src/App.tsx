import { useState } from 'react'

interface Scene {
  scene_number: number
  script_line: string
  scene_type: 'animated' | 'static'
  props: string[]
  style?: string
}

type Step = 'api-key' | 'input-method' | 'script-input' | 'style-selection' | 'generating' | 'results'

function App() {
  const [currentStep, setCurrentStep] = useState<Step>('api-key')
  const [apiKey, setApiKey] = useState('')
  const [inputMethod, setInputMethod] = useState<'file' | 'script'>('script')
  const [script, setScript] = useState('')
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedStyle, setSelectedStyle] = useState('photorealistic')
  const [scenes, setScenes] = useState<Scene[]>([])
  const [generatedImages, setGeneratedImages] = useState<string[]>([])
  const [isGenerating, setIsGenerating] = useState(false)
  const [currentScene, setCurrentScene] = useState(0)
  const [error, setError] = useState<string | null>(null)

  const styles = [
    "photorealistic",
    "animated",
    "3D animation",
    "cartoon",
    "digital art",
    "cinematic",
    "sketch/artistic"
  ]

  const handleApiKeySubmit = () => {
    if (!apiKey.trim()) {
      setError('Please enter your xAI API key')
      return
    }
    setError(null)
    setCurrentStep('input-method')
  }

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (file) {
      setSelectedFile(file)
      setError(null)
    }
  }

  const handleScriptSubmit = () => {
    if (!script.trim()) {
      setError('Please enter a script')
      return
    }
    setError(null)
    setCurrentStep('style-selection')
  }

  const handleStyleSubmit = () => {
    setCurrentStep('generating')
    startGeneration()
  }

  const startGeneration = async () => {
    setIsGenerating(true)
    setError(null)

    try {
      let response;
      if (inputMethod === 'script') {
        response = await fetch('http://localhost:5000/api/generate-from-script', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            api_key: apiKey,
            script: script,
            style: selectedStyle
          }),
        });
      } else {
        const formData = new FormData();
        formData.append('api_key', apiKey);
        if (selectedFile) {
          formData.append('file', selectedFile);
        }

        response = await fetch('http://localhost:5000/api/generate-from-file', {
          method: 'POST',
          body: formData,
        });
      }

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to generate images');
      }

      const data = await response.json();

      setScenes(data.scenes || []);
      setGeneratedImages(data.images.map((filename: string) => `http://localhost:5000/api/images/${filename}`));

      setCurrentStep('results')
    } catch (err) {
      console.error('Generation error:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate images. Please try again.')
    } finally {
      setIsGenerating(false)
    }
  }

  const resetApp = () => {
    setCurrentStep('api-key')
    setApiKey('')
    setScript('')
    setSelectedFile(null)
    setSelectedStyle('photorealistic')
    setScenes([])
    setGeneratedImages([])
    setError(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary-50 to-primary-100">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="text-center mb-12 fade-in">
          <h1 className="text-4xl font-bold text-primary-900 mb-4">
            Script to Images
          </h1>
          <p className="text-lg text-primary-600 max-w-2xl mx-auto">
            Transform your video scripts into AI-generated scene images using xAI Grok.
            Simply provide your API key and upload a script or CSV file.
          </p>
        </div>

        {/* Progress Indicator */}
        <div className="flex justify-center mb-8">
          <div className="flex items-center space-x-4">
            {(['api-key', 'input-method', 'style-selection', 'generating', 'results'] as Step[]).map((step, index) => (
              <div key={step} className="flex items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                  currentStep === step ? 'bg-accent-500 text-white' :
                  ['api-key', 'input-method', 'style-selection', 'generating', 'results'].indexOf(currentStep) > index ? 'bg-accent-100 text-accent-600' :
                  'bg-primary-200 text-primary-400'
                }`}>
                  {index + 1}
                </div>
                {index < 4 && (
                  <div className={`w-12 h-0.5 mx-2 ${
                    ['api-key', 'input-method', 'style-selection', 'generating', 'results'].indexOf(currentStep) > index ? 'bg-accent-500' : 'bg-primary-200'
                  }`} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Main Content */}
        <div className="card slide-up">
          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {/* API Key Step */}
          {currentStep === 'api-key' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold text-primary-900 mb-2">
                  Enter Your xAI API Key
                </h2>
                <p className="text-primary-600">
                  Your API key is stored locally and never sent to our servers.
                </p>
              </div>
              <div>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="xai-..."
                  className="input-field"
                />
              </div>
              <div className="flex justify-end">
                <button onClick={handleApiKeySubmit} className="btn-primary">
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Input Method Selection */}
          {currentStep === 'input-method' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold text-primary-900 mb-2">
                  Choose Input Method
                </h2>
                <p className="text-primary-600">
                  Upload a CSV/JSON file with scenes or enter a script to be automatically parsed.
                </p>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                <button
                  onClick={() => setInputMethod('file')}
                  className={`p-6 border-2 rounded-lg text-left transition-all ${
                    inputMethod === 'file' ? 'border-accent-500 bg-accent-50' : 'border-primary-200 hover:border-primary-300'
                  }`}
                >
                  <h3 className="font-semibold text-primary-900 mb-2">Upload File</h3>
                  <p className="text-primary-600 text-sm">
                    CSV or JSON file with scene_number, script_line, scene_type, and props columns.
                  </p>
                </button>
                <button
                  onClick={() => setInputMethod('script')}
                  className={`p-6 border-2 rounded-lg text-left transition-all ${
                    inputMethod === 'script' ? 'border-accent-500 bg-accent-50' : 'border-primary-200 hover:border-primary-300'
                  }`}
                >
                  <h3 className="font-semibold text-primary-900 mb-2">Enter Script</h3>
                  <p className="text-primary-600 text-sm">
                    Paste your video script and let AI parse it into scenes automatically.
                  </p>
                </button>
              </div>
              {inputMethod === 'file' && (
                <div>
                  <input
                    type="file"
                    accept=".csv,.json"
                    onChange={handleFileSelect}
                    className="input-field"
                  />
                </div>
              )}
              <div className="flex justify-between">
                <button onClick={() => setCurrentStep('api-key')} className="btn-secondary">
                  Back
                </button>
                <button
                  onClick={() => inputMethod === 'file' ? handleStyleSubmit() : setCurrentStep('script-input')}
                  className="btn-primary"
                  disabled={inputMethod === 'file' && !selectedFile}
                >
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Script Input */}
          {currentStep === 'script-input' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold text-primary-900 mb-2">
                  Enter Your Script
                </h2>
                <p className="text-primary-600">
                  Paste your video script. The AI will automatically break it into scenes.
                </p>
              </div>
              <div>
                <textarea
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                  placeholder="Enter your video script here..."
                  rows={10}
                  className="input-field resize-none"
                />
              </div>
              <div className="flex justify-between">
                <button onClick={() => setCurrentStep('input-method')} className="btn-secondary">
                  Back
                </button>
                <button onClick={handleScriptSubmit} className="btn-primary">
                  Continue
                </button>
              </div>
            </div>
          )}

          {/* Style Selection */}
          {currentStep === 'style-selection' && (
            <div className="space-y-6">
              <div>
                <h2 className="text-2xl font-semibold text-primary-900 mb-2">
                  Choose Art Style
                </h2>
                <p className="text-primary-600">
                  Select the visual style for your generated images.
                </p>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {styles.map((style) => (
                  <button
                    key={style}
                    onClick={() => setSelectedStyle(style)}
                    className={`p-4 border-2 rounded-lg text-center transition-all ${
                      selectedStyle === style ? 'border-accent-500 bg-accent-50 text-accent-700' : 'border-primary-200 hover:border-primary-300 text-primary-700'
                    }`}
                  >
                    <span className="font-medium">{style}</span>
                  </button>
                ))}
              </div>
              <div className="flex justify-between">
                <button onClick={() => setCurrentStep('script-input')} className="btn-secondary">
                  Back
                </button>
                <button onClick={handleStyleSubmit} className="btn-primary">
                  Generate Images
                </button>
              </div>
            </div>
          )}

          {/* Generating Progress */}
          {currentStep === 'generating' && (
            <div className="text-center space-y-6">
              <div>
                <h2 className="text-2xl font-semibold text-primary-900 mb-2">
                  Generating Images
                </h2>
                <p className="text-primary-600">
                  Creating scene images using xAI Grok...
                </p>
              </div>
              <div className="space-y-4">
                <div className="w-full bg-primary-200 rounded-full h-2">
                  <div
                    className="bg-accent-500 h-2 rounded-full transition-all duration-500"
                    style={{ width: `${(currentScene / scenes.length) * 100}%` }}
                  />
                </div>
                <p className="text-primary-700">
                  Processing scene {currentScene} of {scenes.length}
                </p>
                {scenes[currentScene - 1] && (
                  <div className="text-left bg-primary-50 p-4 rounded-lg">
                    <p className="font-medium text-primary-900">{scenes[currentScene - 1].script_line}</p>
                    <p className="text-sm text-primary-600">Type: {scenes[currentScene - 1].scene_type} • Props: {scenes[currentScene - 1].props.join(', ')}</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Results Gallery */}
          {currentStep === 'results' && (
            <div className="space-y-6">
              <div className="text-center">
                <h2 className="text-2xl font-semibold text-primary-900 mb-2">
                  Generated Images
                </h2>
                <p className="text-primary-600">
                  Your scene images have been generated successfully!
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {generatedImages.map((imageUrl, index) => (
                  <div key={index} className="space-y-2">
                    <div className="aspect-square bg-primary-100 rounded-lg overflow-hidden">
                      <img
                        src={imageUrl}
                        alt={`Scene ${index + 1}`}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <p className="text-sm text-primary-600 text-center">
                      Scene {String(index + 1).padStart(3, '0')}
                    </p>
                  </div>
                ))}
              </div>
              <div className="flex justify-center space-x-4">
                <button onClick={resetApp} className="btn-secondary">
                  Generate More
                </button>
                <button className="btn-primary">
                  Download All
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default App
