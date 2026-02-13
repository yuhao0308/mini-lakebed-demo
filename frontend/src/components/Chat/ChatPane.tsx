import React, { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import SoftPullCard from '../Consent/SoftPullCard'
import SuggestedQuestions from './SuggestedQuestions'
import { composeQuery } from './SuggestedQuestions'
import type { FilterValues, Suggestion, VehicleCategory } from './SuggestedQuestions'
import { apiService } from '../../services/api'
import './ChatPane.css'

interface Message {
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    tool_calls?: any[]
}

interface ConsentState {
    required: boolean
    customerId: string | null
    vehicleId: number | null
}

/* ──────────────────────────────────────────────
   Suggestion sets — context-aware
   ────────────────────────────────────────────── */

const WELCOME_SUGGESTIONS: Suggestion[] = [
    { icon: '🔍', text: 'Show me Toyota Camry sedans under $30,000', description: 'Search by make, model, and price range' },
    { icon: '🚗', text: 'Show me Honda SUVs', description: 'Browse SUVs from a specific brand' },
    { icon: '🏷️', text: 'Find trucks under $25,000', description: 'Filter by body style and budget' },
]

const AFTER_SEARCH: Suggestion[] = [
    { icon: '👆', text: 'Tell me about the first one' },
    { icon: '🔢', text: 'Tell me about #3' },
]

const AFTER_VEHICLE: Suggestion[] = [
    { icon: '💰', text: 'How much is the monthly payment?' },
    { icon: '✅', text: 'Can I get approved?', tooltip: 'Runs a soft credit check that won\'t affect your credit score. Requires FCRA consent first.' },
    { icon: '🔄', text: 'Show me similar vehicles' },
]

const AFTER_OFFERING_PRICE: Suggestion[] = [
    { icon: '✅', text: 'Can I get approved?', tooltip: 'Runs a soft credit check that won\'t affect your credit score. Requires FCRA consent first.' },
    { icon: '💳', text: 'Set credit & down payment', type: 'credit-input' as const },
]

const AFTER_CONSENT: Suggestion[] = [
    { icon: '💳', text: 'Set credit & down payment', type: 'credit-input' as const },
]

const AFTER_PAYMENT: Suggestion[] = [
    { icon: '🔍', text: 'Show me Honda vehicles' },
    { icon: '✅', text: 'Can I get approved?', tooltip: 'Runs a soft credit check that won\'t affect your credit score. Requires FCRA consent first.' },
]

const createEmptyFilters = (): FilterValues => ({
    price: '',
    year: '',
    brand: '',
    mileage: '',
})

/* ──────────────────────────────────────────────
   Determine which suggestions to show
   ────────────────────────────────────────────── */

function getSuggestions(messages: Message[]): { suggestions: Suggestion[]; variant: 'welcome' | 'inline' } | null {
    if (messages.length <= 1) {
        return { suggestions: WELCOME_SUGGESTIONS, variant: 'welcome' }
    }

    const lastAssistant = [...messages].reverse().find(m => m.role === 'assistant')
    if (!lastAssistant) return null

    const tools = lastAssistant.tool_calls || []
    const hasToolType = (name: string) => tools.some((tc: any) => tc.tool === name)

    if (hasToolType('estimate_payment')) return { suggestions: AFTER_PAYMENT, variant: 'inline' }
    if (hasToolType('offering_price') || hasToolType('compliance_check')) return { suggestions: AFTER_OFFERING_PRICE, variant: 'inline' }
    if (hasToolType('get_vehicle')) return { suggestions: AFTER_VEHICLE, variant: 'inline' }
    if (hasToolType('search_inventory')) return { suggestions: AFTER_SEARCH, variant: 'inline' }

    const content = lastAssistant.content.toLowerCase()
    if (content.includes('credit pre-qualification') || content.includes('credit score') || content.includes('describe your credit')) {
        return { suggestions: AFTER_CONSENT, variant: 'inline' }
    }

    return null
}

/* ──────────────────────────────────────────────
   ChatPane component
   ────────────────────────────────────────────── */

const ChatPane: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: 'Hello! I am your Mini-Lakebed agent. I can help you search the vehicle inventory or provide payment estimates. How can I help you today?',
            timestamp: new Date()
        }
    ])
    const [loading, setLoading] = useState(false)
    const [inputValue, setInputValue] = useState('')
    const [selectedCategory, setSelectedCategory] = useState<VehicleCategory | null>(null)
    const [filters, setFilters] = useState<FilterValues>(createEmptyFilters())
    const [consentState, setConsentState] = useState<ConsentState>({
        required: false,
        customerId: null,
        vehicleId: null
    })
    const [consentLoading, setConsentLoading] = useState(false)
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const sessionId = useRef(Math.random().toString(36).substring(7))

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }

    useEffect(() => {
        scrollToBottom()
    }, [messages])

    const handleSendMessage = async (content: string) => {
        const userMsg: Message = {
            role: 'user',
            content,
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMsg])
        setInputValue('')
        setSelectedCategory(null)
        setFilters(createEmptyFilters())
        setLoading(true)

        try {
            const response = await apiService.sendChat(content, sessionId.current)

            const assistantMsg: Message = {
                role: 'assistant',
                content: response.response,
                timestamp: new Date(),
                tool_calls: response.tool_calls
            }

            setMessages(prev => [...prev, assistantMsg])

            if (response.tool_calls) {
                const consentCall = response.tool_calls.find(
                    (tc: any) => tc.tool === 'require_consent' && tc.results?.requires_consent
                )
                if (consentCall) {
                    setConsentState({
                        required: true,
                        customerId: consentCall.params?.customer_id || null,
                        vehicleId: consentCall.params?.vehicle_id || null
                    })
                }
            }
        } catch (error) {
            console.error('Chat error:', error)
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "I'm sorry, I'm having trouble connecting to the brain. Please ensure the backend is running.",
                timestamp: new Date()
            }])
        } finally {
            setLoading(false)
        }
    }

    const handleConsent = async () => {
        if (!consentState.customerId) return

        setConsentLoading(true)
        try {
            const result = await apiService.submitConsent(consentState.customerId)
            if (result.success) {
                setConsentState({ required: false, customerId: null, vehicleId: null })
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: 'Thank you for providing consent. I can now proceed with the credit pre-qualification. Please tell me your approximate credit score or describe your credit (excellent, good, fair, needs work).',
                    timestamp: new Date()
                }])
            } else {
                setMessages(prev => [...prev, {
                    role: 'assistant',
                    content: `There was an issue recording your consent: ${result.error || 'Unknown error'}. Please try again.`,
                    timestamp: new Date()
                }])
            }
        } catch (error) {
            console.error('Consent error:', error)
            setMessages(prev => [...prev, {
                role: 'assistant',
                content: "I'm sorry, there was an error processing your consent. Please try again.",
                timestamp: new Date()
            }])
        } finally {
            setConsentLoading(false)
        }
    }

    const handleCancelConsent = () => {
        setConsentState({ required: false, customerId: null, vehicleId: null })
        setMessages(prev => [...prev, {
            role: 'assistant',
            content: "No problem! If you change your mind about credit pre-qualification, just let me know. Is there anything else I can help you with?",
            timestamp: new Date()
        }])
    }

    const handleSuggestionSelect = (text: string) => {
        setInputValue(text)
        setTimeout(() => {
            const textarea = document.querySelector<HTMLTextAreaElement>('[data-testid="chat-input"]')
            textarea?.focus()
        }, 0)
    }

    const handleCategorySelect = (category: VehicleCategory) => {
        const resetFilters = createEmptyFilters()
        setSelectedCategory(category)
        setFilters(resetFilters)
        setInputValue(composeQuery(category, resetFilters))
    }

    const handleFilterChange = (key: keyof FilterValues, value: string) => {
        if (!selectedCategory) {
            return
        }

        const nextFilters: FilterValues = { ...filters, [key]: value }
        setFilters(nextFilters)
        setInputValue(composeQuery(selectedCategory, nextFilters))
    }

    const handleDismissFilters = () => {
        setSelectedCategory(null)
        setFilters(createEmptyFilters())
    }

    const suggestionData = !loading && !consentState.required ? getSuggestions(messages) : null

    return (
        <div className="chat-pane" data-testid="chat-pane">
            <div className="chat-messages" data-testid="chat-messages">
                {messages.map((msg, idx) => (
                    <MessageBubble key={idx} message={msg} index={idx} />
                ))}

                {suggestionData?.variant === 'welcome' && (
                    <SuggestedQuestions
                        suggestions={suggestionData.suggestions}
                        onSelect={handleSuggestionSelect}
                        variant="welcome"
                        selectedCategory={selectedCategory}
                        filters={filters}
                        onCategorySelect={handleCategorySelect}
                        onFilterChange={handleFilterChange}
                        onDismissFilters={handleDismissFilters}
                    />
                )}

                {consentState.required && (
                    <SoftPullCard
                        onConsent={handleConsent}
                        onCancel={handleCancelConsent}
                        dealerName="Mini-Lakebed Demo Dealer"
                        isLoading={consentLoading}
                    />
                )}
                {loading && (
                    <div className="message assistant typing" data-testid="typing-indicator">
                        <div className="typing-indicator">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {suggestionData?.variant === 'inline' && (
                <div className="chat-suggestions-bar">
                    <SuggestedQuestions
                        suggestions={suggestionData.suggestions}
                        onSelect={handleSuggestionSelect}
                        variant="inline"
                    />
                </div>
            )}

            <div className="chat-footer">
                <ChatInput
                    onSend={handleSendMessage}
                    disabled={loading || consentState.required}
                    value={inputValue}
                    onChange={setInputValue}
                />
            </div>
        </div>
    )
}

export default ChatPane
