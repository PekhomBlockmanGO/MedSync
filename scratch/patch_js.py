import os

html_file = "frontend/app.html"

with open(html_file, "r", encoding="utf-8") as f:
    content = f.read()

js_code = """
<script>
// MedSync Subscription Management
let currentBillingCycle = 'monthly';
let selectedPlan = null;
let currentFamilyId = 1; // Assuming default for now, backend should use session
let currentUserId = 1;

function toggleBilling(cycle) {
    currentBillingCycle = cycle;
    document.querySelectorAll('.sub-toggle-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector(`.sub-toggle-btn[data-mode="${cycle}"]`).classList.add('active');
    
    // Update prices
    document.querySelectorAll('.price-val').forEach(el => {
        el.innerText = '₹' + el.getAttribute(`data-${cycle}`);
    });
    
    document.querySelectorAll('.price-period').forEach(el => {
        el.innerText = `/ ${cycle === 'monthly' ? 'month' : 'year'}`;
    });
    
    if(cycle === 'yearly') {
        document.getElementById('family-save-note').innerText = 'Save 20%';
        document.getElementById('care-save-note').innerText = 'Save 20%';
    } else {
        document.getElementById('family-save-note').innerHTML = '&nbsp;';
        document.getElementById('care-save-note').innerHTML = '&nbsp;';
    }
}

function initiateCheckout(planName) {
    selectedPlan = planName;
    const isYearly = currentBillingCycle === 'yearly';
    let price = planName === 'family' ? (isYearly ? '1499' : '149') : (isYearly ? '2999' : '299');
    let title = planName === 'family' ? 'MedSync Family' : 'MedSync Care+';
    
    document.getElementById('checkout-plan-name').innerText = title;
    document.getElementById('checkout-price').innerText = `₹${price}/${currentBillingCycle}`;
    
    if(isYearly) {
        document.getElementById('checkout-savings').classList.remove('hidden');
    } else {
        document.getElementById('checkout-savings').classList.add('hidden');
    }
    
    document.getElementById('checkout-confirmation-modal').classList.remove('hidden');
}

function closeCheckoutModal() {
    document.getElementById('checkout-confirmation-modal').classList.add('hidden');
}

async function proceedToPayment() {
    const btnText = document.getElementById('payment-btn-text');
    const spinner = document.getElementById('payment-spinner');
    
    btnText.innerText = 'Initializing...';
    spinner.classList.remove('hidden');
    
    try {
        const response = await fetch(`/api/payment/create-checkout?family_id=${currentFamilyId}&user_id=${currentUserId}`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                plan: selectedPlan,
                billing_cycle: currentBillingCycle
            })
        });
        
        if(!response.ok) {
            const err = await response.json();
            alert("Error: " + (err.detail || "Could not initialize payment. Are payments configured?"));
            throw new Error("Payment init failed");
        }
        
        const data = await response.json();
        
        var options = {
            "key": data.key,
            "subscription_id": data.subscription_id,
            "name": data.name,
            "description": data.description,
            "handler": async function (response) {
                // Verify payment
                btnText.innerText = 'Verifying...';
                try {
                    const verifyRes = await fetch(`/api/payment/verify?family_id=${currentFamilyId}&user_id=${currentUserId}&razorpay_payment_id=${response.razorpay_payment_id}&razorpay_subscription_id=${response.razorpay_subscription_id}&razorpay_signature=${response.razorpay_signature}`, {
                        method: 'POST'
                    });
                    
                    if(verifyRes.ok) {
                        alert("🎉 Payment Successful! Welcome to " + data.description);
                        closeCheckoutModal();
                        loadSubscriptionStatus();
                        switchView('dashboard');
                    } else {
                        alert("Payment verification failed.");
                    }
                } catch(e) {
                    alert("Error verifying payment.");
                }
            },
            "theme": {
                "color": "#f43f5e"
            }
        };
        var rzp1 = new Razorpay(options);
        rzp1.on('payment.failed', function (response){
            alert("Payment Failed. Your current plan has not been changed.");
        });
        rzp1.open();
        
    } catch(err) {
        console.error(err);
    } finally {
        btnText.innerText = 'Continue to Payment';
        spinner.classList.add('hidden');
    }
}

async function loadSubscriptionStatus() {
    try {
        const res = await fetch(`/api/subscription/${currentFamilyId}`);
        if(res.ok) {
            const data = await res.json();
            const sec = document.getElementById('manage-subscription-section');
            if(data.plan !== 'free') {
                sec.classList.remove('hidden');
                document.getElementById('current-plan-display').innerText = data.plan === 'family' ? 'MedSync Family' : 'MedSync Care+';
                document.getElementById('current-status-display').innerText = data.status;
            } else {
                sec.classList.add('hidden');
            }
        }
    } catch(e) { console.error(e); }
}

async function cancelSubscription() {
    if(!confirm("Are you sure you want to cancel your subscription? You will retain access until the end of your billing period.")) return;
    try {
        const res = await fetch(`/api/subscription/cancel?family_id=${currentFamilyId}`, {method: 'POST'});
        if(res.ok) {
            alert("Subscription cancelled successfully.");
            loadSubscriptionStatus();
        } else {
            alert("Failed to cancel subscription.");
        }
    } catch(e) { console.error(e); }
}

// Load status on load if in view
document.addEventListener("DOMContentLoaded", () => {
    loadSubscriptionStatus();
});
</script>
</body>
"""

if "MedSync Subscription Management" not in content:
    new_content = content.replace("</body>", js_code)
    with open(html_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    print("Injected JS!")
else:
    print("JS already exists")
