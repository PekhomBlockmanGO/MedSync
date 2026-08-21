import os
import re

html_file = "frontend/app.html"

with open(html_file, "r", encoding="utf-8") as f:
    content = f.read()

# The subscription modal starts at <div id="view-subscription" ... and ends before closing main or script.
# We'll use regex or string replace to swap it out.
# Let's find the boundaries.
start_idx = content.find('<!-- ============================================================ -->\n            <!-- SUBSCRIPTION MODAL                                           -->')
if start_idx == -1:
    print("Could not find subscription modal start!")
    exit(1)

# Find where the main tag closes after view-subscription
end_idx = content.find('</main>', start_idx)

new_subscription_modal = """<!-- ============================================================ -->
            <!-- SUBSCRIPTION MODAL                                           -->
            <!-- ============================================================ -->
            <div id="view-subscription"
                class="hidden animate-fade-in-up w-full h-full flex flex-col items-center overflow-y-auto py-10 relative">
                <div class="relative w-full max-w-5xl mx-auto px-6 py-16">
                    <!-- Header -->
                    <div class="text-center mb-10">
                        <div class="inline-flex items-center gap-2 text-xs font-semibold tracking-widest uppercase text-rose-400 mb-5">
                            <span class="w-1.5 h-1.5 rounded-full bg-rose-400 shadow-[0_0_8px_rgba(251,113,133,0.7)] animate-pulse"></span>
                            MedSync
                        </div>
                        <h1 class="text-4xl md:text-5xl font-bold text-white leading-tight mb-4">
                            Care that scales<br>from <em class="text-rose-500 italic">one person</em> to the whole family
                        </h1>
                        <p class="text-white/50 text-base max-w-md mx-auto leading-relaxed">
                            Pick the plan that fits how much of the household you're looking after — upgrade any time as things change.
                        </p>
                    </div>

                    <!-- Monthly / Yearly Toggle -->
                    <div class="flex justify-center mb-14">
                        <div id="sub-toggle" class="relative inline-flex items-center bg-white/5 border border-white/10 backdrop-blur-xl rounded-full p-1 gap-1">
                            <button class="sub-toggle-btn active" data-mode="monthly" onclick="toggleBilling('monthly')">Monthly</button>
                            <button class="sub-toggle-btn" data-mode="yearly" onclick="toggleBilling('yearly')">Yearly <span class="text-[10.5px] font-bold bg-rose-500/20 text-rose-300 px-2 py-0.5 rounded-full">Save 20%</span></button>
                        </div>
                    </div>

                    <!-- Plans Grid -->
                    <div class="grid grid-cols-1 md:grid-cols-3 gap-5 items-stretch">

                        <!-- Tier 1 — Free -->
                        <div class="plan relative bg-white/[0.045] border border-white/[0.09] backdrop-blur-2xl rounded-2xl p-7 flex flex-col transition-transform hover:-translate-y-1">
                            <div class="text-lg font-bold text-white mb-1">MedSync Free</div>
                            <div class="text-xs text-white/30 leading-relaxed mb-5 min-h-[36px]">For individuals and small households keeping medication routines organized.</div>

                            <div class="flex items-baseline gap-1 mb-1">
                                <span class="text-3xl font-semibold text-white tabular-nums tracking-tight transition-opacity duration-150">₹0</span>
                                <span class="text-xs text-white/30">/ forever</span>
                            </div>
                            <div class="text-[11.5px] text-rose-400 font-semibold mb-5 min-h-[15px]">&nbsp;</div>

                            <button onclick="switchView('dashboard')" id="btn-free" class="w-full py-2.5 rounded-xl text-sm font-bold border border-white/[0.09] bg-white/[0.04] text-white hover:bg-white/[0.08] transition-all mb-5 cursor-pointer">Get Started Free</button>

                            <div class="h-px bg-white/[0.09] mb-4"></div>
                            <ul class="flex flex-col gap-3 flex-1 text-xs text-white/70">
                                <li>✓ Basic medication tracking</li>
                                <li>✓ Daily medication schedule</li>
                                <li>✓ Medicine expiry warnings</li>
                                <li>✓ Limited health-report storage</li>
                                <li>✓ Emergency locator &amp; nearby searches</li>
                            </ul>
                        </div>

                        <!-- Tier 2 — Family (featured) -->
                        <div class="plan relative bg-gradient-to-b from-rose-500/10 to-rose-500/[0.02] border border-rose-500/40 backdrop-blur-2xl rounded-2xl p-7 flex flex-col shadow-[0_24px_60px_-20px_rgba(244,63,94,0.35),inset_0_1px_0_rgba(255,255,255,0.06)] transition-transform hover:-translate-y-2">
                            <div class="absolute -top-3 left-6 bg-rose-500 text-white text-[10.5px] font-bold tracking-wide px-3 py-1 rounded-full shadow-[0_6px_16px_-4px_rgba(244,63,94,0.6)]">MOST POPULAR</div>
                            
                            <div class="text-lg font-bold text-white mb-1">MedSync Family</div>
                            <div class="text-xs text-white/30 leading-relaxed mb-5 min-h-[36px]">For families managing medicines, schedules, and health records together.</div>

                            <div class="flex items-baseline gap-1 mb-1">
                                <span class="price-val text-3xl font-semibold text-white tabular-nums tracking-tight transition-opacity duration-150" data-monthly="149" data-yearly="1499">₹149</span>
                                <span class="price-period text-xs text-white/30">/ month</span>
                            </div>
                            <div class="text-[11.5px] text-rose-400 font-semibold mb-5 min-h-[15px]" id="family-save-note">&nbsp;</div>

                            <button onclick="initiateCheckout('family')" id="btn-family" class="w-full py-2.5 rounded-xl text-sm font-bold bg-gradient-to-b from-rose-400 to-rose-500 text-white border-none hover:brightness-110 transition-all mb-5 cursor-pointer shadow-[0_4px_18px_-4px_rgba(244,63,94,0.55)]">Start Family</button>

                            <div class="h-px bg-white/[0.09] mb-4"></div>
                            <ul class="flex flex-col gap-3 flex-1 text-xs text-white/70">
                                <li class="text-white font-semibold">Everything in Free, plus:</li>
                                <li>✓ Up to 7 family members</li>
                                <li>✓ Shared household medicine stock</li>
                                <li>✓ Family calendar</li>
                                <li>✓ Unlimited prescription storage</li>
                                <li>✓ Caregiver notifications &amp; alerts</li>
                            </ul>
                        </div>

                        <!-- Tier 3 — Care+ -->
                        <div class="plan relative bg-white/[0.045] border border-white/[0.09] backdrop-blur-2xl rounded-2xl p-7 flex flex-col transition-transform hover:-translate-y-1">
                            
                            <div class="text-lg font-bold text-white mb-1">MedSync Care+</div>
                            <div class="text-xs text-white/30 leading-relaxed mb-5 min-h-[36px]">For families providing active medication and health support to loved ones.</div>

                            <div class="flex items-baseline gap-1 mb-1">
                                <span class="price-val text-3xl font-semibold text-white tabular-nums tracking-tight transition-opacity duration-150" data-monthly="299" data-yearly="2999">₹299</span>
                                <span class="price-period text-xs text-white/30">/ month</span>
                            </div>
                            <div class="text-[11.5px] text-rose-400 font-semibold mb-5 min-h-[15px]" id="care-save-note">&nbsp;</div>

                            <button onclick="initiateCheckout('care')" id="btn-care" class="w-full py-2.5 rounded-xl text-sm font-bold border border-white/[0.09] bg-white/[0.04] text-white hover:bg-white/[0.08] transition-all mb-5 cursor-pointer">Start Care+</button>

                            <div class="h-px bg-white/[0.09] mb-4"></div>
                            <ul class="flex flex-col gap-3 flex-1 text-xs text-white/70">
                                <li class="text-white font-semibold">Everything in Family, plus:</li>
                                <li>✓ Multiple caregivers access</li>
                                <li>✓ Missed-dose escalation</li>
                                <li>✓ Medication adherence reports</li>
                                <li>✓ Advanced AI document analysis</li>
                                <li>✓ Priority support</li>
                            </ul>
                        </div>

                    </div>
                    
                    <!-- Manage Subscription Section -->
                    <div id="manage-subscription-section" class="mt-16 p-8 bg-white/5 border border-white/10 rounded-2xl hidden">
                        <h2 class="text-2xl font-bold text-white mb-6">Manage Subscription</h2>
                        <div class="grid grid-cols-2 gap-8">
                            <div>
                                <p class="text-white/50 text-xs mb-1">Current Plan</p>
                                <p class="text-white text-lg font-bold" id="current-plan-display">Free</p>
                                <p class="text-white/50 text-xs mt-4 mb-1">Status</p>
                                <p class="text-emerald-400 text-sm font-semibold" id="current-status-display">Active</p>
                            </div>
                            <div class="flex flex-col items-end justify-center">
                                <button onclick="cancelSubscription()" class="px-4 py-2 border border-rose-500/50 text-rose-400 rounded-lg text-sm hover:bg-rose-500/10 transition">Cancel Subscription</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Checkout Confirmation Modal -->
            <div id="checkout-confirmation-modal" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm hidden">
                <div class="bg-[#1a1c23] border border-white/10 rounded-2xl p-8 max-w-md w-full m-4">
                    <h3 class="text-2xl font-bold text-white mb-2">Confirm Plan</h3>
                    <p class="text-white/60 text-sm mb-6">You're choosing <span id="checkout-plan-name" class="font-bold text-white">MedSync Family</span></p>
                    
                    <div class="bg-white/5 rounded-xl p-4 mb-6 border border-white/10">
                        <div class="flex justify-between items-center text-lg font-bold text-white">
                            <span>Total</span>
                            <span id="checkout-price">₹149/month</span>
                        </div>
                        <p class="text-xs text-rose-400 mt-2 hidden" id="checkout-savings">Save approximately 20% with annual billing.</p>
                    </div>
                    
                    <div class="flex gap-3">
                        <button onclick="closeCheckoutModal()" class="flex-1 py-3 bg-white/10 hover:bg-white/20 text-white rounded-xl font-semibold transition">Cancel</button>
                        <button onclick="proceedToPayment()" id="btn-proceed-payment" class="flex-1 py-3 bg-rose-500 hover:bg-rose-600 text-white rounded-xl font-bold shadow-lg shadow-rose-500/20 transition flex items-center justify-center gap-2">
                            <span id="payment-btn-text">Continue to Payment</span>
                            <div class="hidden w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" id="payment-spinner"></div>
                        </button>
                    </div>
                </div>
            </div>
"""

new_content = content[:start_idx] + new_subscription_modal + "\n        " + content[end_idx:]

with open(html_file, "w", encoding="utf-8") as f:
    f.write(new_content)
print("Updated app.html subscription modal")
