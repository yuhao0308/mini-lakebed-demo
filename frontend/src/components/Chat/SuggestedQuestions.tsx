import React, { useState } from 'react'
import { Info } from 'lucide-react'
import './SuggestedQuestions.css'

export interface Suggestion {
    icon: string
    text: string
    description?: string
    tooltip?: string
    type?: 'credit-input'
}

export type VehicleCategory = {
    id: string
    name: string
    icon: string
    gradient: 'blue' | 'green' | 'amber' | 'red' | 'purple' | 'teal'
    description: string
    queryTemplate: string
}

export type FilterValues = {
    price: string
    year: string
    brand: string
    mileage: string
}

type FilterOption = {
    value: string
    label: string
    query: string
}

interface SuggestedQuestionsProps {
    suggestions: Suggestion[]
    onSelect: (text: string) => void
    variant: 'welcome' | 'inline'
    selectedCategory?: VehicleCategory | null
    filters?: FilterValues
    onCategorySelect?: (category: VehicleCategory) => void
    onFilterChange?: (key: keyof FilterValues, value: string) => void
    onDismissFilters?: () => void
}

interface CreditInputState {
    score: number
    downPayment: number
    tier: string
}

const CREDIT_TIERS = [
    { min: 750, label: 'Excellent', color: '#10b981' },
    { min: 700, label: 'Good', color: '#3b82f6' },
    { min: 650, label: 'Fair', color: '#f59e0b' },
    { min: 0, label: 'Needs Work', color: '#ef4444' },
]

function getTier(score: number) {
    return CREDIT_TIERS.find(t => score >= t.min) || CREDIT_TIERS[CREDIT_TIERS.length - 1]
}

const EMPTY_FILTERS: FilterValues = {
    price: '',
    year: '',
    brand: '',
    mileage: ''
}

export const VEHICLE_CATEGORIES: VehicleCategory[] = [
    {
        id: 'sedans',
        name: 'Sedans',
        icon: '🚙',
        gradient: 'blue',
        description: 'Comfortable daily drivers with great value.',
        queryTemplate: 'Show me sedans'
    },
    {
        id: 'suvs',
        name: 'SUVs',
        icon: '🚗',
        gradient: 'green',
        description: 'Roomy family options with versatile cargo space.',
        queryTemplate: 'Show me SUVs'
    },
    {
        id: 'trucks',
        name: 'Trucks',
        icon: '🛻',
        gradient: 'amber',
        description: 'Built for towing, hauling, and heavy-duty work.',
        queryTemplate: 'Show me trucks'
    },
    {
        id: 'coupes-sports',
        name: 'Coupes & Sports',
        icon: '🏎️',
        gradient: 'red',
        description: 'Performance-focused picks with bold styling.',
        queryTemplate: 'Show me coupes and sports cars'
    },
    {
        id: 'vans-minivans',
        name: 'Vans & Minivans',
        icon: '🚐',
        gradient: 'purple',
        description: 'Flexible seating and storage for bigger groups.',
        queryTemplate: 'Show me vans and minivans'
    },
    {
        id: 'electric-hybrid',
        name: 'Electric & Hybrid',
        icon: '🔋',
        gradient: 'teal',
        description: 'Fuel-saving and all-electric options for modern driving.',
        queryTemplate: 'Show me electric and hybrid vehicles'
    }
]

export const PRICE_OPTIONS: FilterOption[] = [
    { value: '', label: 'Any price', query: '' },
    { value: '25000', label: 'Under $25,000', query: 'under $25,000' },
    { value: '35000', label: 'Under $35,000', query: 'under $35,000' },
    { value: '50000', label: 'Under $50,000', query: 'under $50,000' },
]

export const YEAR_OPTIONS: FilterOption[] = [
    { value: '', label: 'Any year', query: '' },
    { value: '2024', label: '2024 or newer', query: 'from 2024 or newer' },
    { value: '2022', label: '2022 or newer', query: 'from 2022 or newer' },
    { value: '2020', label: '2020 or newer', query: 'from 2020 or newer' },
]

export const BRAND_OPTIONS: FilterOption[] = [
    { value: '', label: 'Any brand', query: '' },
    { value: 'Toyota', label: 'Toyota', query: '' },
    { value: 'Honda', label: 'Honda', query: '' },
    { value: 'Ford', label: 'Ford', query: '' },
    { value: 'Chevrolet', label: 'Chevrolet', query: '' },
    { value: 'Nissan', label: 'Nissan', query: '' },
    { value: 'BMW', label: 'BMW', query: '' },
    { value: 'Tesla', label: 'Tesla', query: '' },
]

export const MILEAGE_OPTIONS: FilterOption[] = [
    { value: '', label: 'Any mileage', query: '' },
    { value: '30000', label: 'Under 30,000 miles', query: 'with under 30,000 miles' },
    { value: '50000', label: 'Under 50,000 miles', query: 'with under 50,000 miles' },
    { value: '80000', label: 'Under 80,000 miles', query: 'with under 80,000 miles' },
]

const getFilterQuery = (options: FilterOption[], value: string): string => {
    if (!value) return ''
    return options.find(option => option.value === value)?.query || ''
}

export function composeQuery(category: VehicleCategory, filters: FilterValues): string {
    const brandPrefix = filters.brand ? `${filters.brand} ` : ''
    const baseQuery = `Show me ${brandPrefix}${category.name}`
    const filterQueries = [
        getFilterQuery(PRICE_OPTIONS, filters.price),
        getFilterQuery(YEAR_OPTIONS, filters.year),
        getFilterQuery(MILEAGE_OPTIONS, filters.mileage),
    ].filter(Boolean)

    if (!filters.brand && filterQueries.length === 0) {
        return category.queryTemplate
    }

    if (filterQueries.length === 0) {
        return baseQuery
    }

    return `${baseQuery} ${filterQueries.join(' ')}`
}

interface FilterBarProps {
    filters: FilterValues
    onFilterChange: (key: keyof FilterValues, value: string) => void
    onDismiss: () => void
}

const FilterBar: React.FC<FilterBarProps> = ({ filters, onFilterChange, onDismiss }) => {
    return (
        <div className="filter-bar">
            <div className="filter-select-wrapper">
                <select
                    className={`filter-dropdown ${filters.price ? 'filter-active' : ''}`}
                    value={filters.price}
                    onChange={(event) => onFilterChange('price', event.target.value)}
                    aria-label="Filter by price"
                >
                    {PRICE_OPTIONS.map(option => (
                        <option key={option.value || 'any-price'} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            </div>
            <div className="filter-select-wrapper">
                <select
                    className={`filter-dropdown ${filters.year ? 'filter-active' : ''}`}
                    value={filters.year}
                    onChange={(event) => onFilterChange('year', event.target.value)}
                    aria-label="Filter by year"
                >
                    {YEAR_OPTIONS.map(option => (
                        <option key={option.value || 'any-year'} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            </div>
            <div className="filter-select-wrapper">
                <select
                    className={`filter-dropdown ${filters.brand ? 'filter-active' : ''}`}
                    value={filters.brand}
                    onChange={(event) => onFilterChange('brand', event.target.value)}
                    aria-label="Filter by brand"
                >
                    {BRAND_OPTIONS.map(option => (
                        <option key={option.value || 'any-brand'} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            </div>
            <div className="filter-select-wrapper">
                <select
                    className={`filter-dropdown ${filters.mileage ? 'filter-active' : ''}`}
                    value={filters.mileage}
                    onChange={(event) => onFilterChange('mileage', event.target.value)}
                    aria-label="Filter by mileage"
                >
                    {MILEAGE_OPTIONS.map(option => (
                        <option key={option.value || 'any-mileage'} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
            </div>
            <button className="filter-dismiss" onClick={onDismiss}>
                Dismiss
            </button>
        </div>
    )
}

interface WelcomeExplorerProps {
    onSelect: (text: string) => void
    selectedCategory?: VehicleCategory | null
    filters?: FilterValues
    onCategorySelect?: (category: VehicleCategory) => void
    onFilterChange?: (key: keyof FilterValues, value: string) => void
    onDismissFilters?: () => void
}

const WelcomeExplorer: React.FC<WelcomeExplorerProps> = ({
    onSelect,
    selectedCategory,
    filters,
    onCategorySelect,
    onFilterChange,
    onDismissFilters
}) => {
    const [localSelectedCategory, setLocalSelectedCategory] = useState<VehicleCategory | null>(null)
    const [localFilters, setLocalFilters] = useState<FilterValues>({ ...EMPTY_FILTERS })

    const controlledMode = (
        selectedCategory !== undefined &&
        filters !== undefined &&
        onCategorySelect !== undefined &&
        onFilterChange !== undefined &&
        onDismissFilters !== undefined
    )

    const activeCategory = controlledMode ? selectedCategory : localSelectedCategory
    const activeFilters = controlledMode ? (filters as FilterValues) : localFilters

    const handleCategoryClick = (category: VehicleCategory) => {
        if (controlledMode) {
            onCategorySelect(category)
            return
        }

        const resetFilters = { ...EMPTY_FILTERS }
        setLocalSelectedCategory(category)
        setLocalFilters(resetFilters)
        onSelect(composeQuery(category, resetFilters))
    }

    const handleFilterUpdate = (key: keyof FilterValues, value: string) => {
        if (!activeCategory) {
            return
        }

        if (controlledMode) {
            onFilterChange(key, value)
            return
        }

        const nextFilters: FilterValues = { ...localFilters, [key]: value }
        setLocalFilters(nextFilters)
        onSelect(composeQuery(activeCategory, nextFilters))
    }

    const handleDismiss = () => {
        if (controlledMode) {
            onDismissFilters()
            return
        }

        setLocalSelectedCategory(null)
        setLocalFilters({ ...EMPTY_FILTERS })
    }

    return (
        <div className="welcome-explorer">
            <div className="welcome-explorer-header">
                <div className="welcome-explorer-title">Explore by vehicle type</div>
                <div className="welcome-explorer-subtitle">Pick a category to start, then refine with quick filters.</div>
            </div>

            <div className="category-grid">
                {VEHICLE_CATEGORIES.map((category, index) => (
                    <button
                        key={category.id}
                        className={`category-card gradient-${category.gradient} ${activeCategory?.id === category.id ? 'selected' : ''}`}
                        style={{ animationDelay: `${index * 60}ms` }}
                        onClick={() => handleCategoryClick(category)}
                    >
                        <span className="category-icon">{category.icon}</span>
                        <span className="category-name">{category.name}</span>
                        <span className="category-description">{category.description}</span>
                    </button>
                ))}
            </div>

            {activeCategory && (
                <FilterBar
                    filters={activeFilters}
                    onFilterChange={handleFilterUpdate}
                    onDismiss={handleDismiss}
                />
            )}
        </div>
    )
}

const CreditInputPanel: React.FC<{ onSelect: (text: string) => void }> = ({ onSelect }) => {
    const [state, setState] = useState<CreditInputState>({ score: 720, downPayment: 3000, tier: 'Good' })
    const tier = getTier(state.score)

    const handleApply = () => {
        const tierLabel = tier.label.toLowerCase()
        onSelect(`I have ${tierLabel} credit, score around ${state.score}, and $${state.downPayment.toLocaleString()} down`)
    }

    return (
        <div className="credit-input-panel">
            <div className="credit-input-header">
                <span className="credit-input-icon">💳</span>
                <span className="credit-input-title">Set Your Credit Details</span>
            </div>

            <div className="credit-slider-group">
                <div className="credit-slider-label">
                    <span>Credit Score</span>
                    <span className="credit-score-value" style={{ color: tier.color }}>
                        {state.score} <span className="credit-tier-badge" style={{ background: tier.color }}>{tier.label}</span>
                    </span>
                </div>
                <input
                    type="range"
                    className="credit-slider"
                    min={500}
                    max={850}
                    step={10}
                    value={state.score}
                    onChange={e => setState(s => ({ ...s, score: +e.target.value }))}
                    style={{ '--slider-color': tier.color } as React.CSSProperties}
                />
                <div className="credit-slider-range">
                    <span>500</span><span>850</span>
                </div>
            </div>

            <div className="credit-slider-group">
                <div className="credit-slider-label">
                    <span>Down Payment</span>
                    <span className="credit-down-value">${state.downPayment.toLocaleString()}</span>
                </div>
                <input
                    type="range"
                    className="credit-slider"
                    min={0}
                    max={20000}
                    step={500}
                    value={state.downPayment}
                    onChange={e => setState(s => ({ ...s, downPayment: +e.target.value }))}
                />
                <div className="credit-slider-range">
                    <span>$0</span><span>$20,000</span>
                </div>
            </div>

            <button className="credit-apply-btn" onClick={handleApply}>
                Fill in Chat
            </button>
        </div>
    )
}

const SuggestedQuestions: React.FC<SuggestedQuestionsProps> = ({
    suggestions,
    onSelect,
    variant,
    selectedCategory,
    filters,
    onCategorySelect,
    onFilterChange,
    onDismissFilters
}) => {
    const [activeCreditPanel, setActiveCreditPanel] = useState(false)

    if (variant === 'welcome') {
        return (
            <WelcomeExplorer
                onSelect={onSelect}
                selectedCategory={selectedCategory}
                filters={filters}
                onCategorySelect={onCategorySelect}
                onFilterChange={onFilterChange}
                onDismissFilters={onDismissFilters}
            />
        )
    }

    return (
        <div className="suggestions-inline-wrapper">
            <div className="suggestions-inline">
                {suggestions.map((s, i) => {
                    if (s.type === 'credit-input') {
                        return (
                            <div key={i} className="suggestion-pill-container">
                                <button
                                    className={`suggestion-pill ${activeCreditPanel ? 'active' : ''}`}
                                    onClick={() => setActiveCreditPanel(v => !v)}
                                >
                                    <span className="pill-icon">{s.icon}</span>
                                    {s.text}
                                </button>
                                {activeCreditPanel && (
                                    <CreditInputPanel onSelect={(text) => { setActiveCreditPanel(false); onSelect(text) }} />
                                )}
                            </div>
                        )
                    }

                    return (
                        <div key={i} className="suggestion-pill-container">
                            <button
                                className="suggestion-pill"
                                onClick={() => onSelect(s.text)}
                            >
                                <span className="pill-icon">{s.icon}</span>
                                {s.text}
                            </button>
                            {s.tooltip && (
                                <div className="suggestion-tooltip-anchor">
                                    <Info size={14} className="suggestion-info-icon" />
                                    <div className="suggestion-tooltip">{s.tooltip}</div>
                                </div>
                            )}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

export default SuggestedQuestions
