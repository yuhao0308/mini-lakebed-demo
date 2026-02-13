import React, { useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import { Send, Image, Mic } from 'lucide-react'
import './ChatInput.css'

interface ChatInputProps {
    onSend: (message: string) => void
    disabled?: boolean
    value: string
    onChange: (value: string) => void
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled, value, onChange }) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    const handleSend = () => {
        if (value.trim() && !disabled) {
            onSend(value)
            onChange('')
        }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = textareaRef.current.scrollHeight + 'px'
        }
    }, [value])

    return (
        <div className="chat-input-wrapper">
            <div className="chat-input-container">
                <button className="icon-btn" disabled={disabled} title="Upload Image">
                    <Image size={20} />
                </button>
                <button className="icon-btn" disabled={disabled} title="Voice Input">
                    <Mic size={20} />
                </button>

                <textarea
                    ref={textareaRef}
                    className="chat-textarea"
                    rows={1}
                    placeholder="Ask about inventory or payments..."
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    data-testid="chat-input"
                />

                <button
                    className="send-btn"
                    onClick={handleSend}
                    disabled={!value.trim() || disabled}
                    data-testid="chat-send-button"
                >
                    <Send size={18} />
                </button>
            </div>
        </div>
    )
}

export default ChatInput
