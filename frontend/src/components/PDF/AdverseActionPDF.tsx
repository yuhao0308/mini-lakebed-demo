import React from 'react'
import { FileDown, AlertTriangle, CheckCircle } from 'lucide-react'
import './AdverseActionPDF.css'

interface Reason {
    code: string
    text: string
}

interface CounterOffer {
    adjustedTermMonths: number
    adjustedApr: number
    adjustedMonthlyPayment: number
    requiredDownPayment: number
}

interface AdverseActionNotice {
    noticeId: string
    applicantName: string
    decisionDate: string
    bureauSource: string
    scoreDate: string
    reasons: Reason[]
    counterOffer?: CounterOffer
}

interface AdverseActionPDFProps {
    notice: AdverseActionNotice
    onDownload?: () => void
    downloadUrl?: string
    language?: 'en' | 'es'
}

const translations = {
    en: {
        title: 'Credit Decision',
        reasonsTitle: 'Principal Reasons for This Decision',
        counterOfferTitle: 'Alternative Terms Available',
        downloadPdf: 'Download Formal Notice (PDF)',
        bureauInfo: 'Bureau Information',
        counterOfferDetails: {
            term: 'Term',
            apr: 'APR',
            payment: 'Monthly Payment',
            downPayment: 'Required Down Payment'
        },
        disclaimer: 'This notice is provided in compliance with the Equal Credit Opportunity Act (Regulation B).'
    },
    es: {
        title: 'Decisión de Crédito',
        reasonsTitle: 'Razones Principales de Esta Decisión',
        counterOfferTitle: 'Términos Alternativos Disponibles',
        downloadPdf: 'Descargar Aviso Formal (PDF)',
        bureauInfo: 'Información del Buró',
        counterOfferDetails: {
            term: 'Plazo',
            apr: 'APR',
            payment: 'Pago Mensual',
            downPayment: 'Pago Inicial Requerido'
        },
        disclaimer: 'Este aviso se proporciona en cumplimiento con la Ley de Igualdad de Oportunidad de Crédito (Regulación B).'
    }
}

const AdverseActionPDF: React.FC<AdverseActionPDFProps> = ({
    notice,
    onDownload,
    downloadUrl,
    language = 'en'
}) => {
    const t = translations[language]

    const handleDownload = () => {
        if (onDownload) {
            onDownload()
        } else if (downloadUrl) {
            window.open(downloadUrl, '_blank')
        }
    }

    return (
        <div className="adverse-action-card">
            <div className="card-header">
                <AlertTriangle size={20} className="icon warning" />
                <h3>{t.title}</h3>
            </div>

            <div className="applicant-info">
                <span className="applicant-name">{notice.applicantName}</span>
                <span className="decision-date">{notice.decisionDate}</span>
            </div>

            <div className="reasons-section">
                <h4>{t.reasonsTitle}</h4>
                <ul className="reasons-list">
                    {notice.reasons.map((reason, idx) => (
                        <li key={reason.code}>
                            <span className="reason-number">{idx + 1}</span>
                            <span className="reason-text">{reason.text}</span>
                            <span className="reason-code">({reason.code})</span>
                        </li>
                    ))}
                </ul>
            </div>

            <div className="bureau-info">
                <h4>{t.bureauInfo}</h4>
                <p>
                    <strong>Source:</strong> {notice.bureauSource}
                </p>
                <p>
                    <strong>Score Date:</strong> {notice.scoreDate}
                </p>
            </div>

            {notice.counterOffer && (
                <div className="counter-offer-section">
                    <div className="counter-offer-header">
                        <CheckCircle size={18} className="icon success" />
                        <h4>{t.counterOfferTitle}</h4>
                    </div>
                    <div className="counter-offer-details">
                        <div className="detail">
                            <span className="label">{t.counterOfferDetails.term}</span>
                            <span className="value">{notice.counterOffer.adjustedTermMonths} months</span>
                        </div>
                        <div className="detail">
                            <span className="label">{t.counterOfferDetails.apr}</span>
                            <span className="value">{notice.counterOffer.adjustedApr}%</span>
                        </div>
                        <div className="detail">
                            <span className="label">{t.counterOfferDetails.payment}</span>
                            <span className="value">${notice.counterOffer.adjustedMonthlyPayment.toFixed(2)}</span>
                        </div>
                        <div className="detail">
                            <span className="label">{t.counterOfferDetails.downPayment}</span>
                            <span className="value">${notice.counterOffer.requiredDownPayment.toLocaleString()}</span>
                        </div>
                    </div>
                </div>
            )}

            <button className="download-button" onClick={handleDownload}>
                <FileDown size={18} />
                <span>{t.downloadPdf}</span>
            </button>

            <p className="disclaimer">{t.disclaimer}</p>
        </div>
    )
}

export default AdverseActionPDF
