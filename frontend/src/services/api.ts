import type { Lake, Zone, Asset } from '../types';

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');
const TUNNEL_SECRET = import.meta.env.VITE_TUNNEL_SECRET || '';

function apiHeaders(extra: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { 'Content-Type': 'application/json', ...extra };
    if (TUNNEL_SECRET) headers['X-Tunnel-Secret'] = TUNNEL_SECRET;
    return headers;
}

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
        const response = await fetch(`${API_BASE_URL}/api/chat`, {
            method: 'POST',
            headers: apiHeaders(),
            body: JSON.stringify({ message, session_id: sessionId })
        });
        return response.json();
    },

    // T03: FCRA consent submission
    submitConsent: async (customerId: string, consentType: string = 'soft_pull', legalTextVersion: string = 'v2026.1') => {
        const response = await fetch(`${API_BASE_URL}/api/consent`, {
            method: 'POST',
            headers: apiHeaders(),
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
        const response = await fetch(`${API_BASE_URL}/api/consent/check/${customerId}`, {
            headers: apiHeaders()
        });
        return response.json();
    },

    // T03: Get consent legal text
    getConsentLegalText: async (version: string = 'v2026.1', dealerName: string = 'Mini-Lakebed Demo Dealer') => {
        const response = await fetch(`${API_BASE_URL}/api/consent/legal-text?version=${version}&dealer_name=${encodeURIComponent(dealerName)}`, {
            headers: apiHeaders()
        });
        return response.json();
    },

    // T06: Download adverse action PDF
    downloadAdverseActionPdf: async (noticeData: any, language: string = 'en') => {
        const response = await fetch(`${API_BASE_URL}/api/documents/adverse-action/pdf`, {
            method: 'POST',
            headers: apiHeaders(),
            body: JSON.stringify({ ...noticeData, language })
        });
        return response.blob();
    },

    // T06: Download offering price PDF
    downloadOfferingPricePdf: async (vehicle: any, components: any, language: string = 'en') => {
        const response = await fetch(`${API_BASE_URL}/api/documents/offering-price/pdf`, {
            method: 'POST',
            headers: apiHeaders(),
            body: JSON.stringify({ vehicle, components, language })
        });
        return response.blob();
    },

    // T06: Get sample adverse action PDF
    getSampleAdverseActionPdf: async (language: string = 'en') => {
        const response = await fetch(`${API_BASE_URL}/api/documents/adverse-action/sample?language=${language}`, {
            headers: apiHeaders()
        });
        return response.blob();
    },

    // T06: Get sample offering price PDF
    getSampleOfferingPricePdf: async (language: string = 'en') => {
        const response = await fetch(`${API_BASE_URL}/api/documents/offering-price/sample?language=${language}`, {
            headers: apiHeaders()
        });
        return response.blob();
    }
};
