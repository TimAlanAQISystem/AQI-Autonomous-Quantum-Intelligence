# AQI Agent Portal Integration - Technical Discovery Call Preparation

**Date:** December 15, 2025
**Meeting:** 11:00 AM CT (Central Time)
**Purpose:** Technical discovery for AQI backend integration with Agent Portal
**Prepared by:** TimAlanAQISystem

---

## 🎯 Executive Summary

AQI will integrate with the Agent Portal using OAuth2 client credentials flow with webhook notifications for real-time merchant status and transaction updates. All authentication will be handled through AQI's secure token management system with automatic refresh capabilities.

---

## 📋 Pre-Call Checklist

### ✅ Technical Readiness
- [ ] Confirm AQI backend environment (dev/staging/prod)
- [ ] Verify webhook callback URL availability
- [ ] Prepare test merchant data for demonstration
- [ ] Review AQI authentication architecture
- [ ] Confirm compliance requirements (PCI, SOC2, etc.)

### ✅ Documentation Ready
- [ ] API key vs OAuth2 preference documented
- [ ] Webhook event requirements specified
- [ ] Callback URL prepared (or placeholder)
- [ ] Security requirements reviewed
- [ ] Integration timeline estimated

### ✅ Call Logistics
- [ ] Sales Engineering ticket created/opened
- [ ] Meeting invite accepted with calendar reminder
- [ ] Technical team availability confirmed
- [ ] Demo environment prepared (if needed)

---

## 🔐 Technical Answers - Ready for Call

### 1. API Keys & Authentication
**Our Position:** OAuth2 Client Credentials Flow
- **Why:** More secure than static API keys, supports token rotation
- **Implementation:** AQI backend will handle token storage, refresh, and scope management
- **Storage:** Encrypted at rest, rotated automatically
- **Fallback:** Can support API key if OAuth2 unavailable

### 2. Webhooks / Push Notifications
**Our Requirements:**
- **Events Needed:**
  - `merchant.status_update` - Real-time status changes
  - `merchant.approval` - Approval confirmations
  - `merchant.decline` - Decline notifications with reasons
  - `transaction.confirmation` - Transaction completions
  - `transaction.failure` - Failed transactions with error codes

- **Callback URL:** `https://api.aqi-system.com/webhooks/agent-portal/v1/events`
- **Security:** HMAC-SHA256 signature validation required
- **Retry Logic:** Exponential backoff (3 retries, 30s intervals)
- **Format:** JSON payload with event type, timestamp, and data

### 3. OAuth2 Authorization Flow
**Our Implementation:**
- **Flow Type:** Client Credentials Grant
- **Scopes Required:**
  - `merchants:read` - Access merchant data
  - `merchants:write` - Update merchant status
  - `transactions:read` - Access transaction history
  - `webhooks:manage` - Configure webhook endpoints

- **Token Management:**
  - Automatic refresh 5 minutes before expiry
  - Secure storage with encryption
  - Token rotation on security events
  - Revocation handling for compromised tokens

### 4. Sales Engineering Ticket
**Status:** Ready to create
**Priority:** High (Integration Planning)
**Components:**
- AQI backend integration requirements
- Authentication flow specification
- Webhook configuration details
- Security and compliance requirements
- Testing and validation procedures

---

## 📞 Call Script - Technical Discovery Meeting

### Opening (First 2 minutes)
"Good morning/afternoon [Engineer Name]. Thanks for taking this discovery call. I'm Tim Alan from AQI Autonomous Intelligence. We're excited to integrate our AQI backend with your Agent Portal to enable automated merchant support workflows.

Before we dive in, I wanted to confirm - did you receive the Sales Engineering ticket I opened? If not, I can create it right now with our integration requirements."

### Technical Overview (5 minutes)
"Let me give you a quick overview of what we're building. AQI is an autonomous intelligence system that handles merchant support interactions. We want to integrate with your Agent Portal to:

1. **Automate merchant onboarding** - Real-time status updates
2. **Handle transaction inquiries** - Direct API access to transaction data
3. **Provide proactive support** - Webhook notifications for issues

Our architecture is built on Python with a secure microservices approach, and we're SOC2 compliant."

### Authentication Discussion (5-7 minutes)
**You:** "For authentication, we're planning to use OAuth2 client credentials flow. This gives us the security and token management we need. Does your system support this, or would we need to use API keys?"

**Expected Response:** Listen for their preference and constraints.

**Follow-up:** "Our backend handles token refresh automatically and stores them encrypted. We can support scopes for different access levels - merchants, transactions, webhooks, etc."

### Webhooks Discussion (5-7 minutes)
**You:** "We definitely want webhook notifications enabled. Specifically, we need real-time updates for:
- Merchant status changes (pending → approved → active)
- Transaction confirmations and failures
- Any critical alerts

Our callback URL will be: `https://api.aqi-system.com/webhooks/agent-portal/v1/events`

We'll implement HMAC signature validation and proper retry logic. What format do you use for webhook payloads?"

**Expected Response:** Get their webhook specification details.

### Security & Compliance (3-5 minutes)
**You:** "Security is paramount for us. We're SOC2 Type II compliant and handle PCI data. For the integration:
- All data transmission will be HTTPS with TLS 1.3
- Tokens stored encrypted with automatic rotation
- Webhook signatures validated on every request
- Audit logging for all API interactions

Do you have any specific security requirements or compliance certifications we should be aware of?"

### Next Steps & Timeline (3-5 minutes)
**You:** "From our side, once we have the authentication details and webhook specs, our engineering team can have a basic integration ready within 1-2 weeks for testing.

What would be your recommended next steps? Should we schedule a technical deep-dive, or do you need anything else from us before then?"

### Closing (2 minutes)
"Thanks for your time today. This was very helpful. I'll follow up with any additional details you need, and we'll get that integration moving forward.

Have a great rest of your day!"

---

## 📊 Technical Summary - Read Verbatim if Needed

"AQI Autonomous Intelligence requires integration with the Agent Portal API for automated merchant support capabilities. Our system needs:

**Authentication:** OAuth2 client credentials flow with automatic token refresh and encrypted storage.

**Webhooks:** Real-time notifications for merchant status updates, transaction confirmations, and critical alerts. Callback URL: https://api.aqi-system.com/webhooks/agent-portal/v1/events with HMAC-SHA256 validation.

**API Access:** Read/write access to merchant data and transaction history with appropriate scoping.

**Security:** SOC2 compliant with TLS 1.3 encryption, audit logging, and secure token management.

**Timeline:** Ready to begin development immediately upon receiving API specifications and sandbox access."

---

## 🎫 Sales Engineering Ticket Draft

### Subject: AQI Agent Portal Integration - Technical Discovery & Requirements

**Priority:** High
**Type:** Integration Request
**Requester:** Tim Alan (AQI Autonomous Intelligence)
**Discovery Call:** December 15, 2025 - 11:00 AM CT

### Business Context
AQI is building autonomous merchant support capabilities and requires API integration with the Agent Portal to enable real-time merchant status monitoring, transaction data access, and automated support workflows.

### Technical Requirements

#### Authentication
- **Preferred Method:** OAuth2 Client Credentials Grant
- **Scopes Required:**
  - `merchants:read` - Access merchant profile and status data
  - `merchants:write` - Update merchant status and metadata
  - `transactions:read` - Access transaction history and details
  - `webhooks:manage` - Configure and manage webhook endpoints
- **Token Management:** Automatic refresh and rotation required

#### Webhooks
- **Events Required:**
  - Merchant status updates (pending → approved → active → suspended)
  - Transaction confirmations and failures
  - Critical system alerts
- **Callback URL:** `https://api.aqi-system.com/webhooks/agent-portal/v1/events`
- **Security:** HMAC-SHA256 signature validation
- **Retry Logic:** Support for webhook retry with exponential backoff

#### API Endpoints
- Merchant management endpoints
- Transaction history and status APIs
- Webhook configuration endpoints

### Security & Compliance
- SOC2 Type II compliant system
- PCI DSS compliant for transaction data handling
- TLS 1.3 encryption required
- Audit logging for all API interactions
- Secure token storage with encryption

### Environment Requirements
- Sandbox environment for testing
- API documentation and OpenAPI specifications
- Rate limiting and quota information
- Error response formats

### Timeline
- API specifications needed: Immediately
- Sandbox access: Within 1 week
- Basic integration complete: 2 weeks
- Production deployment: 4-6 weeks

### Points of Contact
- Technical Lead: Tim Alan
- Email: [your contact email]
- Phone: [your phone number]

### Next Steps
1. Provide API documentation and sandbox credentials
2. Schedule technical deep-dive meeting
3. Confirm authentication and webhook specifications
4. Begin integration development

---

## ⚡ Quick Reference Cards

### Authentication Decision Tree
```
Do they support OAuth2?
├── YES → Use OAuth2 client credentials
│   ├── Automatic token refresh
│   ├── Scope-based access
│   └── Encrypted storage
└── NO → Use API keys
    ├── Static key management
    ├── Manual rotation
    └── Secure storage required
```

### Webhook Events Priority
1. **Critical:** `merchant.suspended`, `transaction.failed`
2. **High:** `merchant.approved`, `transaction.confirmed`
3. **Medium:** `merchant.status_update`, `transaction.pending`
4. **Low:** `system.health_check`, `merchant.created`

### Security Checklist
- [ ] TLS 1.3 encryption
- [ ] HMAC signature validation
- [ ] Token encryption at rest
- [ ] Audit logging enabled
- [ ] Rate limiting understood
- [ ] Error handling implemented

---

**Remember:** Stay technical but not overwhelming. Focus on requirements, not implementation details. Listen more than you talk. If you get stuck, refer to this document.

**Good luck on the call!** 🚀