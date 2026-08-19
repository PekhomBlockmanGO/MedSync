with open('frontend/app.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, l in enumerate(lines):
    if '<div id="add-med-modal"' in l:
        pass
    if '            <p class="foot-note">Prices in USD. Cancel any time' in l:
        if start_idx == -1:
            start_idx = i - 2  # Go up 2 lines (should be line 1369)
    if '        </main>' in l:
        end_idx = i
        break

if start_idx != -1 and end_idx != -1:
    print(f"Removing lines from {start_idx} to {end_idx - 1}")
    
    new_sub = """
            <!-- ========================================== -->
            <!-- SUBSCRIPTION VIEW                          -->
            <!-- ========================================== -->
            <div id="view-subscription" class="hidden h-full flex-col items-center justify-start overflow-y-auto pt-8 pb-20 w-full">
                <div class="relative w-full max-w-6xl bg-white/5 border border-white/20 rounded-3xl shadow-2xl overflow-hidden p-8 backdrop-blur-xl">
                    <div class="wrap text-white">
                        <div class="eyebrow text-brand-400"><span class="dot bg-brand-400"></span> Curo Health</div>
                        <h1 class="text-white">Care that scales<br><em class="text-brand-400 font-italic">from one person</em> to the whole family</h1>
                        <p class="sub text-gray-400">Pick the plan that fits how much of the household you're looking after — upgrade any time as things change.</p>
                      
                        <div class="toggle-row">
                          <div class="toggle border border-white/20 bg-white/10 backdrop-blur-md" id="sub-toggle">
                            <div class="toggle-thumb bg-gradient-to-b from-brand-400 to-brand-600"></div>
                            <button class="active text-white" data-mode="monthly">Monthly</button>
                            <button class="text-gray-400" data-mode="yearly">Yearly <span class="save-pill bg-white/20 text-white">Save 20%</span></button>
                          </div>
                        </div>
                      
                        <div class="plans-scroll">
                            <div class="plans flex gap-5 min-w-[780px]">
                      
                              <!-- Tier 1 — Starter -->
                              <div class="plan flex-1 bg-white/5 border border-white/20 backdrop-blur-xl rounded-2xl p-6 flex flex-col hover:-translate-y-1 transition-transform">
                                <div class="plan-icon bg-white/10 border border-white/20 w-10 h-10 rounded-xl flex items-center justify-center mb-4">
                                  <svg viewBox="0 0 24 24" fill="none"><path d="M12 3v18M5 8l7-5 7 5" stroke="#fff" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
                                </div>
                                <div class="plan-name text-xl font-bold text-white mb-2">Starter</div>
                                <div class="plan-audience text-xs text-gray-400 mb-5 min-h-[36px]">For one person keeping their own medication schedule on track.</div>
                          
                                <div class="price-row flex items-baseline gap-1 mb-1">
                                  <span class="price text-3xl font-bold text-white" data-monthly="0" data-yearly="0">$0</span>
                                  <span class="price-period text-xs text-gray-400">/ forever</span>
                                </div>
                                <div class="price-note text-xs font-semibold text-brand-400 mb-5 min-h-[15px]">&nbsp;</div>
                          
                                <button class="cta w-full py-2.5 bg-white/10 border border-white/20 text-white rounded-lg font-bold hover:bg-white/20 mb-6 transition-colors" onclick="switchView('patient')">Get started free</button>
                          
                                <div class="divider h-[1px] bg-white/20 mb-4"></div>
                                <ul class="features flex flex-col gap-3 flex-1">
                                  <li class="lead flex gap-2 text-sm text-white font-semibold"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Basic medication tracking &amp; daily schedule</li>
                                  <li class="flex gap-2 text-sm text-gray-400"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Stock health alerts — expired or running low</li>
                                  <li class="flex gap-2 text-sm text-gray-400"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Limited AI Assistant queries — Quick Ask</li>
                                </ul>
                              </div>
                          
                              <!-- Tier 2 — Family Hub (featured) -->
                              <div class="plan featured relative flex-1 bg-gradient-to-b from-brand-600/20 to-brand-600/5 border border-brand-500/50 backdrop-blur-xl rounded-2xl p-6 flex flex-col hover:-translate-y-2 transition-transform shadow-[0_24px_60px_-20px_rgba(244,63,94,0.35)]">
                                <div class="ribbon absolute -top-3 left-6 bg-brand-500 text-white text-[10.5px] font-bold px-3 py-1 rounded-full shadow-[0_6px_16px_-4px_rgba(244,63,94,0.6)]">Most families choose this</div>
                                <div class="plan-icon bg-brand-500/20 border border-brand-500/40 w-10 h-10 rounded-xl flex items-center justify-center mb-4">
                                  <svg viewBox="0 0 24 24" fill="none"><circle cx="8" cy="8" r="3" stroke="#f43f5e" stroke-width="1.6"/><circle cx="17" cy="8" r="3" stroke="#f43f5e" stroke-width="1.6"/><path d="M2.5 20c.6-3.6 3-5.5 5.5-5.5S13.4 16.4 14 20M13 20c.5-3 2.4-4.7 4.5-4.7s3.8 1.7 4 4.7" stroke="#f43f5e" stroke-width="1.6" stroke-linecap="round"/></svg>
                                </div>
                                <div class="plan-name text-xl font-bold text-white mb-2">Family Hub</div>
                                <div class="plan-audience text-xs text-gray-300 mb-5 min-h-[36px]">For households managing medication across multiple members and devices.</div>
                          
                                <div class="price-row flex items-baseline gap-1 mb-1">
                                  <span class="price text-3xl font-bold text-white" data-monthly="9.99" data-yearly="7.99">$9.99</span>
                                  <span class="price-period text-xs text-gray-300">/ mo</span>
                                </div>
                                <div class="price-note text-xs font-semibold text-brand-400 mb-5 min-h-[15px]" data-yearly-note>&nbsp;</div>
                          
                                <button class="cta w-full py-2.5 bg-gradient-to-b from-brand-400 to-brand-600 text-white border-none rounded-lg font-bold hover:brightness-110 mb-6 transition-all" onclick="switchView('patient')">Start Family Hub</button>
                          
                                <div class="divider h-[1px] bg-white/20 mb-4"></div>
                                <ul class="features flex flex-col gap-3 flex-1">
                                  <li class="lead flex gap-2 text-sm text-white font-semibold"><span class="check w-4 h-4 rounded-full bg-brand-500/30 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Everything in Starter, plus:</li>
                                  <li class="flex gap-2 text-sm text-gray-300"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Full multi-user account switching — Mom, Dad, patient profiles</li>
                                  <li class="flex gap-2 text-sm text-gray-300"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Unlimited AI bottle scanning + interaction analysis</li>
                                  <li class="flex gap-2 text-sm text-gray-300"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Caregiver alerts for missed doses</li>
                                  <li class="flex gap-2 text-sm text-gray-300"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Shared family calendar view</li>
                                </ul>
                              </div>
                          
                              <!-- Tier 3 — Concierge -->
                              <div class="plan flex-1 bg-white/5 border border-white/20 backdrop-blur-xl rounded-2xl p-6 flex flex-col hover:-translate-y-1 transition-transform">
                                <div class="plan-icon bg-white/10 border border-white/20 w-10 h-10 rounded-xl flex items-center justify-center mb-4">
                                  <svg viewBox="0 0 24 24" fill="none"><path d="M12 2l2.6 5.8L21 9l-4.7 4.1L17.5 20 12 16.5 6.5 20l1.2-6.9L3 9l6.4-1.2L12 2z" stroke="#fff" stroke-width="1.4" stroke-linejoin="round"/></svg>
                                </div>
                                <div class="plan-name text-xl font-bold text-white mb-2">Concierge</div>
                                <div class="plan-audience text-xs text-gray-400 mb-5 min-h-[36px]">For power users coordinating aging parents' care with nurses or clinics.</div>
                          
                                <div class="price-row flex items-baseline gap-1 mb-1">
                                  <span class="price text-3xl font-bold text-white" data-monthly="24.99" data-yearly="19.99">$24.99</span>
                                  <span class="price-period text-xs text-gray-400">/ mo</span>
                                </div>
                                <div class="price-note text-xs font-semibold text-brand-400 mb-5 min-h-[15px]" data-yearly-note>&nbsp;</div>
                          
                                <button class="cta w-full py-2.5 bg-white/10 border border-white/20 text-white rounded-lg font-bold hover:bg-white/20 mb-6 transition-colors" onclick="switchView('patient')">Talk to us</button>
                          
                                <div class="divider h-[1px] bg-white/20 mb-4"></div>
                                <ul class="features flex flex-col gap-3 flex-1">
                                  <li class="lead flex gap-2 text-sm text-white font-semibold"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Everything in Family Hub, plus:</li>
                                  <li class="flex gap-2 text-sm text-gray-400"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Real-time emergency alerts to doctors &amp; care providers</li>
                                  <li class="flex gap-2 text-sm text-gray-400"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Adherence analytics — weekly/monthly PDF reports</li>
                                  <li class="flex gap-2 text-sm text-gray-400"><span class="check w-4 h-4 rounded-full bg-brand-500/20 flex items-center justify-center mt-0.5"><svg viewBox="0 0 12 12"><path d="M2 6.5l2.5 2.5L10 3" stroke="#fb7185" stroke-width="1.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></span>Priority 24/7 AI support</li>
                                </ul>
                              </div>
                          
                            </div>
                        </div>
                        <p class="foot-note text-center text-xs text-gray-500 mt-10">Prices in USD. Cancel any time — annual plans billed once per year.</p>
                    </div>
                </div>
            </div>\n"""
            
    new_lines = lines[:start_idx] + [new_sub] + lines[end_idx:]
    with open('frontend/app.html', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Replaced successfully.")
else:
    print(f"Could not find indices: start={start_idx}, end={end_idx}")
