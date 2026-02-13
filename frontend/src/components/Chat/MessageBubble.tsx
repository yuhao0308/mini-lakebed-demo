import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { User, Bot, Database } from 'lucide-react'
import InventoryCard from '../Common/InventoryCard'
import PaymentCard from '../Common/PaymentCard'
import OfferingPrice from '../Common/OfferingPrice'
import PaymentBreakdown from '../Deal/PaymentBreakdown'
import AdverseActionPDF from '../PDF/AdverseActionPDF'
import CancellationOption from '../Disclosure/CancellationOption'
import './MessageBubble.css'

interface Message {
    role: 'user' | 'assistant'
    content: string
    timestamp: Date
    tool_calls?: any[]
}

interface MessageBubbleProps {
    message: Message
    index?: number
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message, index }) => {
    const isAssistant = message.role === 'assistant'

    return (
        <div
            className={`message-container ${message.role}`}
            data-testid={`message-${message.role}${index !== undefined ? `-${index}` : ''}`}
        >
            <div className="avatar-wrapper">
                <div className={`avatar ${message.role}`}>
                    {isAssistant ? <Bot size={18} /> : <User size={18} />}
                </div>
            </div>

            <div className="message-content-wrapper">
                <div className="message-bubble" data-testid={`message-content-${index !== undefined ? index : 'unknown'}`}>
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {message.content}
                    </ReactMarkdown>
                </div>

                {message.tool_calls && message.tool_calls.length > 0 && (
                    <div className="tool-results" data-testid={`tool-results-${index !== undefined ? index : 'unknown'}`}>
                        {message.tool_calls.map((call, idx) => {
                            if (call.tool === 'search_inventory' && call.results?.vehicles) {
                                return (
                                    <div key={idx} className="horizontal-scroll" data-testid="inventory-results">
                                        {call.results.vehicles.map((v: any, vIdx: number) => (
                                            <InventoryCard key={v.id} vehicle={v} index={vIdx} />
                                        ))}
                                    </div>
                                )
                            }
                            if (call.tool === 'estimate_payment' && call.results?.estimate) {
                                return (
                                    <div key={idx} data-testid="payment-estimate-result">
                                        <PaymentCard
                                            estimate={call.results.estimate}
                                            ruleId={call.results.audit?.rule_id}
                                        />
                                    </div>
                                )
                            }
                            // T06: Offering price display
                            if (call.tool === 'offering_price' && call.results?.vehicle) {
                                return (
                                    <OfferingPrice
                                        key={idx}
                                        vehicle={call.results.vehicle}
                                        components={call.results.components}
                                    />
                                )
                            }
                            // T06: Payment breakdown with interactive fields
                            if (call.tool === 'payment_breakdown' && call.results?.dealStructure) {
                                return (
                                    <PaymentBreakdown
                                        key={idx}
                                        vehicle={call.results.vehicle}
                                        customer={call.results.customer}
                                        dealStructure={call.results.dealStructure}
                                        editable={call.results.editable !== false}
                                    />
                                )
                            }
                            // T06: Adverse action notice with PDF download
                            if (call.tool === 'adverse_action' && call.results?.notice) {
                                return (
                                    <AdverseActionPDF
                                        key={idx}
                                        notice={call.results.notice}
                                        downloadUrl={call.results.downloadUrl}
                                    />
                                )
                            }
                            // T06: CA cancellation disclosure
                            if (call.tool === 'cancellation_option' && call.results?.vehicle) {
                                return (
                                    <CancellationOption
                                        key={idx}
                                        vehicle={call.results.vehicle}
                                        show={call.results.show}
                                        customerState={call.results.customerState}
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
