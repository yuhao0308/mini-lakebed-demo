import React, { useState } from 'react'
import type { KeyboardEvent } from 'react'
import { Send, Image, Mic } from 'lucide-react'
import './ChatInput.css'

interface ChatInputProps {
    onSend: (message: string) => void
    disabled?: boolean
}

const ChatInput: React.FC<ChatInputProps> = ({ onSend, disabled }) => {
    const [value, setValue] = useState('')

    const handleSend = () => {
        if (value.trim() && !disabled) {
            onSend(value)
            setValue('')
        }
    }

    const handleKeyDown = (e: KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

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
                    className="chat-textarea"
                    rows={1}
                    placeholder="Ask about inventory or payments..."
                    value={value}
                    onChange={(e) => setValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                />

                <button
                    className="send-btn"
                    onClick={handleSend}
                    disabled={!value.trim() || disabled}
                >
                    <Send size={18} />
                </button>
            </div>
        </div>
    )
}

export default ChatInput
