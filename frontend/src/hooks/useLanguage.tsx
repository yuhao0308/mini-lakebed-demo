import { useState, useEffect, useCallback, createContext, useContext } from 'react'
import enTranslations from '../i18n/en.json'
import esTranslations from '../i18n/es.json'

export type Language = 'en' | 'es'

type TranslationKeys = typeof enTranslations

interface LanguageContextType {
    language: Language
    setLanguage: (lang: Language) => void
    t: (key: string, params?: Record<string, string>) => string
    translations: TranslationKeys
}

const translations: Record<Language, TranslationKeys> = {
    en: enTranslations,
    es: esTranslations
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined)

/**
 * Detect browser language preference
 */
const detectLanguage = (): Language => {
    const browserLang = navigator.language.split('-')[0]
    if (browserLang === 'es') return 'es'
    return 'en'
}

/**
 * Get stored language preference
 */
const getStoredLanguage = (): Language | null => {
    try {
        const stored = localStorage.getItem('language')
        if (stored === 'en' || stored === 'es') return stored
        return null
    } catch {
        return null
    }
}

/**
 * Store language preference
 */
const storeLanguage = (lang: Language): void => {
    try {
        localStorage.setItem('language', lang)
    } catch {
        // localStorage not available
    }
}

/**
 * Get nested object value by dot-notation key
 */
const getNestedValue = (obj: any, key: string): string | undefined => {
    const keys = key.split('.')
    let value: any = obj

    for (const k of keys) {
        if (value && typeof value === 'object' && k in value) {
            value = value[k]
        } else {
            return undefined
        }
    }

    return typeof value === 'string' ? value : undefined
}

/**
 * Replace template parameters in string
 */
const interpolate = (str: string, params: Record<string, string>): string => {
    return str.replace(/\{(\w+)\}/g, (_, key) => params[key] || `{${key}}`)
}

/**
 * Hook for language detection and switching
 */
export const useLanguage = () => {
    const [language, setLanguageState] = useState<Language>(() => {
        return getStoredLanguage() || detectLanguage()
    })

    const setLanguage = useCallback((lang: Language) => {
        setLanguageState(lang)
        storeLanguage(lang)
    }, [])

    const t = useCallback((key: string, params?: Record<string, string>): string => {
        const value = getNestedValue(translations[language], key)
        if (!value) {
            console.warn(`Translation missing for key: ${key}`)
            return key
        }
        return params ? interpolate(value, params) : value
    }, [language])

    useEffect(() => {
        // Update document lang attribute
        document.documentElement.lang = language
    }, [language])

    return {
        language,
        setLanguage,
        t,
        translations: translations[language]
    }
}

/**
 * Language Provider component
 */
export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const languageState = useLanguage()

    return (
        <LanguageContext.Provider value={languageState}>
            {children}
        </LanguageContext.Provider>
    )
}

/**
 * Hook to use language context
 */
export const useLanguageContext = (): LanguageContextType => {
    const context = useContext(LanguageContext)
    if (!context) {
        throw new Error('useLanguageContext must be used within a LanguageProvider')
    }
    return context
}

export default useLanguage
