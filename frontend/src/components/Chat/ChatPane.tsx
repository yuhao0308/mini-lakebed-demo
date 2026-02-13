import React, { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import ChatInput, { type ComposerChip } from './ChatInput'
import SoftPullCard from '../Consent/SoftPullCard'
import SuggestedQuestions from './SuggestedQuestions'
import { composeQuery } from './SuggestedQuestions'
import type { FilterValues, Suggestion, VehicleCategory } from './SuggestedQuestions'
import type { Vehicle } from '../../types'
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

const MAX_COMPOSER_VEHICLES = 3
const SINGLE_AUTO_PROMPT = 'Tell me about this vehicle'
const MULTI_AUTO_PROMPT = 'Compare these vehicles'

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
    const [composerVehicles, setComposerVehicles] = useState<Vehicle[]>([])
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

    const isAutoPrompt = (text: string): boolean => (
        text === SINGLE_AUTO_PROMPT || text === MULTI_AUTO_PROMPT
    )

    const getAutoPrompt = (vehicleCount: number): string => (
        vehicleCount > 1 ? MULTI_AUTO_PROMPT : SINGLE_AUTO_PROMPT
    )

    const focusComposerInput = () => {
        setTimeout(() => {
            const textarea = document.querySelector<HTMLTextAreaElement>('[data-testid="chat-input"]')
            textarea?.focus()
        }, 0)
    }

    const handleSendMessage = async (content: string) => {
        const userMsg: Message = {
            role: 'user',
            content,
            timestamp: new Date()
        }

        setMessages(prev => [...prev, userMsg])
        setInputValue('')
        setComposerVehicles([])
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
        focusComposerInput()
    }

    const handleToggleVehicleComposerSelection = (vehicle: Vehicle) => {
        if (loading || consentState.required) {
            return
        }

        setComposerVehicles(prev => {
            const exists = prev.some(item => item.id === vehicle.id)
            let next: Vehicle[]

            if (exists) {
                next = prev.filter(item => item.id !== vehicle.id)
            } else if (prev.length >= MAX_COMPOSER_VEHICLES) {
                next = [...prev.slice(1), vehicle]
            } else {
                next = [...prev, vehicle]
            }

            setInputValue(current => {
                if (next.length === 0) {
                    return isAutoPrompt(current) ? '' : current
                }

                if (!current.trim() || isAutoPrompt(current)) {
                    return getAutoPrompt(next.length)
                }

                return current
            })

            return next
        })

        focusComposerInput()
    }

    const handleRemoveComposerVehicle = (vehicleId: number) => {
        setComposerVehicles(prev => {
            const next = prev.filter(item => item.id !== vehicleId)
            setInputValue(current => {
                if (next.length === 0) {
                    return isAutoPrompt(current) ? '' : current
                }

                if (isAutoPrompt(current)) {
                    return getAutoPrompt(next.length)
                }

                return current
            })
            return next
        })

        focusComposerInput()
    }

    const buildComposerMessage = (draftText: string): string => {
        const baseText = draftText.trim()
        if (composerVehicles.length === 0) {
            return baseText
        }

        const selectedReferences = composerVehicles
            .map((vehicle, idx) => {
                const trimPart = vehicle.trim ? ` ${vehicle.trim}` : ''
                return `${idx + 1}) vehicle ID ${vehicle.id} (${vehicle.year} ${vehicle.make} ${vehicle.model}${trimPart})`
            })
            .join('; ')

        const promptText = baseText || getAutoPrompt(composerVehicles.length)
        return `${promptText}\nSelected vehicles: ${selectedReferences}`
    }

    const handleComposerSend = (draftText: string) => {
        const composedMessage = buildComposerMessage(draftText)
        if (!composedMessage.trim()) {
            return
        }

        void handleSendMessage(composedMessage)
    }

    const handleRequestVehicleDetails = (vehicle: Vehicle, position?: number) => {
        if (loading || consentState.required) {
            return
        }

        const trimPart = vehicle.trim ? ` ${vehicle.trim}` : ''
        const vehicleLabel = `${vehicle.year} ${vehicle.make} ${vehicle.model}${trimPart}`
        const prompt = position
            ? `Tell me about #${position} (${vehicleLabel}, vehicle ID ${vehicle.id}) with full details.`
            : `Show full details for vehicle ID ${vehicle.id} (${vehicleLabel}).`

        void handleSendMessage(prompt)
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
                    <MessageBubble
                        key={idx}
                        message={msg}
                        index={idx}
                        onRequestVehicleDetails={handleRequestVehicleDetails}
                        onToggleVehicleComposerSelection={handleToggleVehicleComposerSelection}
                        selectedComposerVehicleIds={composerVehicles.map(vehicle => vehicle.id)}
                        actionsDisabled={loading || consentState.required}
                    />
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
                {composerVehicles.length > 0 && (
                    <div className="composer-selection-meta">
                        {composerVehicles.length}/{MAX_COMPOSER_VEHICLES} vehicles selected
                    </div>
                )}
                <ChatInput
                    onSend={handleComposerSend}
                    disabled={loading || consentState.required}
                    value={inputValue}
                    onChange={setInputValue}
                    chips={composerVehicles.map((vehicle): ComposerChip => {
                        const trimPart = vehicle.trim ? ` ${vehicle.trim}` : ''
                        return {
                            id: vehicle.id,
                            label: `${vehicle.year} ${vehicle.make} ${vehicle.model}${trimPart} • ID ${vehicle.id}`
                        }
                    })}
                    onRemoveChip={handleRemoveComposerVehicle}
                />
            </div>
        </div>
    )
}

export default ChatPane
