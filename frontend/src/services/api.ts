import type { Lake, Zone, Asset } from '../types';

const MOCK_LAKES: Lake[] = [
    {
        name: 'projects/demo/locations/us-central1/lakes/finance',
        ui_id: 'finance',
        display_name: 'Finance Lake',
        create_time: '2025-12-01T10:00:00Z',
        update_time: '2025-12-01T10:00:00Z'
    },
    {
        name: 'projects/demo/locations/us-central1/lakes/marketing',
        ui_id: 'marketing',
        display_name: 'Marketing Lake',
        create_time: '2025-12-05T12:00:00Z',
        update_time: '2025-12-05T12:00:00Z'
    }
];

const MOCK_ZONES: Record<string, Zone[]> = {
    'finance': [
        { name: '.../zones/raw', ui_id: 'raw', type: 'RAW', create_time: '2025-12-01T10:05:00Z' },
        { name: '.../zones/curated', ui_id: 'curated', type: 'CURATED', create_time: '2025-12-01T10:10:00Z' }
    ],
    'marketing': [
        { name: '.../zones/sandbox', ui_id: 'sandbox', type: 'SANDBOX', create_time: '2025-12-05T12:05:00Z' }
    ]
};

const MOCK_ASSETS: Record<string, Asset[]> = {
    'raw': [
        { name: '.../assets/transactions_2024', ui_id: 'transactions_2024', resource_path: 'gs://finance-raw/trans_2024/', schema: 'avro', create_time: '2025-12-01T11:00:00Z' },
        { name: '.../assets/customer_leads', ui_id: 'customer_leads', resource_path: 'gs://finance-raw/leads/', schema: 'csv', create_time: '2025-12-02T09:30:00Z' }
    ],
    'curated': [
        { name: '.../assets/inventory_governed', ui_id: 'inventory_governed', resource_path: 'sqlite://mini_lakebed.db/inventory', schema: 'sql', create_time: '2025-12-19T18:00:00Z' }
    ]
};

export const apiService = {
    getLakes: async (): Promise<Lake[]> => {
        return new Promise((resolve) => setTimeout(() => resolve(MOCK_LAKES), 400));
    },

    getZones: async (lakeId: string): Promise<Zone[]> => {
        return new Promise((resolve) => setTimeout(() => resolve(MOCK_ZONES[lakeId] || []), 300));
    },

    getAssets: async (zoneId: string): Promise<Asset[]> => {
        return new Promise((resolve) => setTimeout(() => resolve(MOCK_ASSETS[zoneId] || []), 300));
    },

    // Real backend call
    sendChat: async (message: string, sessionId: string) => {
        const response = await fetch('http://localhost:8000/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId })
        });
        return response.json();
    },

    // T03: FCRA consent submission
    submitConsent: async (customerId: string, consentType: string = 'soft_pull', legalTextVersion: string = 'v2026.1') => {
        const response = await fetch('http://localhost:8000/api/consent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                customer_id: customerId,
                consent_type: consentType,
                legal_text_version: legalTextVersion
            })
        });
        return response.json();
    },

    // T03: Check consent status
    checkConsent: async (customerId: string) => {
        const response = await fetch(`http://localhost:8000/api/consent/check/${customerId}`);
        return response.json();
    },

    // T03: Get consent legal text
    getConsentLegalText: async (version: string = 'v2026.1', dealerName: string = 'Mini-Lakebed Demo Dealer') => {
        const response = await fetch(`http://localhost:8000/api/consent/legal-text?version=${version}&dealer_name=${encodeURIComponent(dealerName)}`);
        return response.json();
    }
};
