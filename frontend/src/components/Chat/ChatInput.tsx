import React, { useRef, useEffect } from 'react'
import type { KeyboardEvent } from 'react'
import { Send, Image, Mic, X } from 'lucide-react'
import './ChatInput.css'

export interface ComposerChip {
    id: number
    label: string
}

interface ChatInputProps {
    onSend: (message: string) => void
    disabled?: boolean
    value: string
    onChange: (value: string) => void
    chips?: ComposerChip[]
    onRemoveChip?: (chipId: number) => void
}

const ChatInput: React.FC<ChatInputProps> = ({
    onSend,
    disabled,
    value,
    onChange,
    chips = [],
    onRemoveChip
}) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const hasSendPayload = value.trim().length > 0 || chips.length > 0

    const handleSend = () => {
        if (hasSendPayload && !disabled) {
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
            {chips.length > 0 && (
                <div className="chat-chip-row" data-testid="composer-chip-row">
                    {chips.map(chip => (
                        <button
                            key={chip.id}
                            type="button"
                            className="composer-chip"
                            onClick={() => onRemoveChip?.(chip.id)}
                            disabled={disabled}
                            title="Remove vehicle from message"
                        >
                            <span className="composer-chip-label">{chip.label}</span>
                            <X size={12} className="composer-chip-remove" />
                        </button>
                    ))}
                </div>
            )}
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
                    disabled={!hasSendPayload || disabled}
                    data-testid="chat-send-button"
                >
                    <Send size={18} />
                </button>
            </div>
        </div>
    )
}

export default ChatInput
