import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { User, Bot, Database } from 'lucide-react'
import InventoryCard from '../Common/InventoryCard'
import PaymentCard from '../Common/PaymentCard'
import './MessageBubble.css'

interface Message {
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    tool_calls?: any[]
}

const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
    const isAssistant = message.role === 'assistant'

    return (
        <div className={`message-container ${message.role}`}>
            <div className="avatar-wrapper">
                <div className={`avatar ${message.role}`}>
                    {isAssistant ? <Bot size={18} /> : <User size={18} />}
                </div>
            </div>

            <div className="message-content-wrapper">
                <div className="message-bubble">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                    </ReactMarkdown>
                </div>

                {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="tool-results">
                        {message.tool_calls.map((call, idx) => {
                            if (call.tool === 'search_inventory' && call.results?.vehicles) {
                                return (
                                    <div key={idx} className="horizontal-scroll">
                                        {call.results.vehicles.map((v: any) => (
                                            <InventoryCard key={v.id} vehicle={v} />
                                        ))}
                                    </div>
                                )
                            }
                            if (call.tool === 'estimate_payment' && call.results?.estimate) {
                                return (
                                    <PaymentCard
                                        key={idx}
                                        estimate={call.results.estimate}
                                        ruleId={call.results.audit?.rule_id}
                                    />
                                )
                            }
                            return (
                                <div key={idx} className="tool-badge">
                                    <Database size={12} />
                                    <span>{call.tool}</span>
                                </div>
                            )
                        })}
                    </div>
                )}

                <span className="timestamp">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                </span>
            </div>
        </div>
    )
}

export default MessageBubble
