import React, { useState, useRef, useEffect } from 'react'
import MessageBubble from './MessageBubble'
import ChatInput from './ChatInput'
import SoftPullCard from '../Consent/SoftPullCard'
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

const ChatPane: React.FC = () => {
    const [messages, setMessages] = useState<Message[]>([
        {
            role: 'assistant',
            content: 'Hello! I am your Mini-Lakebed agent. I can help you search the vehicle inventory or provide payment estimates. How can I help you today?',
            timestamp: new Date()
        }
    ])
    const [loading, setLoading] = useState(false)
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

            // T03: Check if consent is required
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

    // T03: Handle consent submission
    const handleConsent = async () => {
        if (!consentState.customerId) return

        setConsentLoading(true)
        try {
            const result = await apiService.submitConsent(consentState.customerId)
            if (result.success) {
                setConsentState({ required: false, customerId: null, vehicleId: null })

                // Add system message about consent
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

    // T03: Handle consent cancellation
    const handleCancelConsent = () => {
        setConsentState({ required: false, customerId: null, vehicleId: null })
        setMessages(prev => [...prev, {
            role: 'assistant',
            content: "No problem! If you change your mind about credit pre-qualification, just let me know. Is there anything else I can help you with?",
            timestamp: new Date()
        }])
    }

    return (
        <div className="chat-pane">
            <div className="chat-messages">
                {messages.map((msg, idx) => (
                    <MessageBubble key={idx} message={msg} />
                ))}
                {/* T03: Render SoftPullCard when consent is required */}
                {consentState.required && (
                    <SoftPullCard
                        onConsent={handleConsent}
                        onCancel={handleCancelConsent}
                        dealerName="Mini-Lakebed Demo Dealer"
                        isLoading={consentLoading}
                    />
                )}
                {loading && (
                    <div className="message assistant typing">
                        <div className="typing-indicator">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            <div className="chat-footer">
                <ChatInput onSend={handleSendMessage} disabled={loading || consentState.required} />
            </div>
        </div>
    )
}

export default ChatPane
