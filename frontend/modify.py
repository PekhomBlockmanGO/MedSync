import re

with open("frontend/app.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Extract the Subscription Modal
sub_start_marker = "<!-- SUBSCRIPTION MODAL                                           -->"
sub_regex = re.compile(
    r"<!-- ============================================================ -->\s*" + 
    re.escape(sub_start_marker) + r"\s*" +
    r"<!-- ============================================================ -->\s*" +
    r"<div id=\"view-subscription\".*?</div>\s*</div>\s*</div>", re.DOTALL)

match = sub_regex.search(content)
if not match:
    print("Could not find subscription modal block")
    exit(1)

sub_html = match.group(0)

# Remove it from its original location
content = content.replace(sub_html, "")

# 2. Modify the Subscription HTML to be a regular view
# Remove the modal classes and change it to the tab view classes: hidden animate-fade-in-up w-full h-full
sub_html = re.sub(
    r'<div id="view-subscription" class="hidden fixed inset-0 z-50 bg-black/95 backdrop-blur-2xl overflow-y-auto flex items-center justify-center p-4 md:p-8">',
    r'<div id="view-subscription" class="hidden animate-fade-in-up w-full h-full flex flex-col items-center justify-start pt-8 pb-20">',
    sub_html
)
# Update inner container to be more full-width and remove its modal background
sub_html = re.sub(
    r'<div class="relative w-full max-w-6xl bg-black/80 border border-white/20 rounded-3xl shadow-2xl overflow-hidden p-8">',
    r'<div class="relative w-full max-w-6xl bg-white/5 border border-white/20 rounded-3xl shadow-2xl overflow-hidden p-8 backdrop-blur-xl">',
    sub_html
)

# Remove the Close button completely
sub_html = re.sub(
    r'<button class="close-btn".*?</button>',
    '',
    sub_html
)

# 3. Insert the new Subscription HTML before </main>
# <main ...> ... </main>
main_end = "</main>"
content = content.replace(main_end, sub_html + "\n        " + main_end)

# 4. Update the sidebar Subscription button onclick handler
content = content.replace(
    '''onclick="document.getElementById('view-subscription').classList.remove('hidden')"''',
    '''onclick="switchView('subscription')"'''
)

# 5. Update the JS switchView function
switch_view_target = '''            // Hide all first
            [patientView, caregiverView, calendarView].forEach(view => {'''
switch_view_replacement = '''            const subscriptionView = document.getElementById('view-subscription');
            
            // Hide all first
            [patientView, caregiverView, calendarView, subscriptionView].forEach(view => {'''
content = content.replace(switch_view_target, switch_view_replacement)

# Also add the else if block for subscription
calendar_block = '''            } else if (tabName === 'calendar') {
                if(calendarView) {
                    calendarView.classList.remove('hidden');
                    calendarView.classList.add('block');
                }
                // Optional: Initialize or fetch calendar data here if needed
            }'''
subscription_block = calendar_block + ''' else if (tabName === 'subscription') {
                if (subscriptionView) {
                    subscriptionView.classList.remove('hidden');
                    subscriptionView.classList.add('block');
                }
            }'''
content = content.replace(calendar_block, subscription_block)


with open("frontend/app.html", "w", encoding="utf-8") as f:
    f.write(content)

print("Done")
