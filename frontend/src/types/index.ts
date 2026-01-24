export interface Lake {
    name: string;
    ui_id: string;
    display_name: string;
    create_time: string;
    update_time: string;
}

export interface Zone {
    name: string;
    ui_id: string;
    type: 'RAW' | 'CURATED' | 'SANDBOX';
    create_time: string;
}

export interface Asset {
    name: string;
    ui_id: string;
    resource_path: string;
    schema: string;
    create_time: string;
}

export interface Vehicle {
    id: number;
    vin: string;
    make: string;
    model: string;
    year: number;
    trim?: string;
    price: number;
    mileage: number;
    body_style: string;
    status: string;
}

export interface PaymentEstimate {
    monthly_payment: number;
    apr: number;
    term_months: number;
    principal: number;
    total_interest: number;
    total_cost: number;
}
