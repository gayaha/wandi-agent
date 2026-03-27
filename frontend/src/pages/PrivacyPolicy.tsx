const PrivacyPolicy = () => {
  return (
    <div className="min-h-screen bg-slate-900 py-12 px-4" dir="ltr">
      <div className="max-w-3xl mx-auto bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-8">
        <h1 className="text-3xl font-bold text-white mb-2">Privacy Policy</h1>
        <p className="text-slate-400 text-sm mb-8">Wandi AI</p>

        <div className="space-y-8 text-slate-300 leading-relaxed">
          <section>
            <h2 className="text-xl font-semibold text-white mb-2">1. Introduction</h2>
            <p>
              Welcome to Wandi AI. We operate the Wandi AI application, providing automation, AI-driven content generation, and social media marketing services via Meta platforms (Facebook and Instagram).
            </p>
            <p className="mt-2">
              This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our services.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">2. Information We Collect</h2>
            <h3 className="text-lg font-medium text-white mt-4 mb-2">A. Data We Access Through Meta APIs</h3>
            <p>
              When you connect your Facebook Page or Instagram account to Wandi AI, we request access to specific data through the Meta Graph API. We only access data that is necessary to provide our services.
            </p>
            <p className="mt-3 font-medium text-white">Specific Permissions We Request:</p>
            <ul className="list-disc list-inside space-y-1 mt-2">
              <li><code className="text-purple-300">instagram_basic</code> - To access basic Instagram account information.</li>
              <li><code className="text-purple-300">instagram_content_publish</code> - To publish photos, videos, reels, and stories to your Instagram account.</li>
              <li><code className="text-purple-300">read_engagement</code> - To read engagement data and page information.</li>
              <li><code className="text-purple-300">pages_show_list</code> - To display a list of Pages you manage for account selection.</li>
              <li><code className="text-purple-300">business_management</code> - To manage business assets and access business-level information for your connected Pages.</li>
            </ul>

            <h3 className="text-lg font-medium text-white mt-4 mb-2">B. Data You Provide Directly</h3>
            <ul className="list-disc list-inside space-y-1">
              <li><strong className="text-white">Media Files:</strong> Photos, videos, and captions you provide for publishing on social media.</li>
              <li><strong className="text-white">AI Content Inputs:</strong> Text prompts, brand guidelines, and creative briefs you submit for AI-generated content.</li>
              <li><strong className="text-white">Contact Information:</strong> Your name, email address, or phone number provided during onboarding or communication.</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">3. How We Use Your Information</h2>
            <p>We use the information we collect for content creation, scheduling, publishing, account management, service communication, and service improvement.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">4. Data Security</h2>
            <p>We implement industry-standard technical and organizational measures to protect your data, including encryption at rest, row-level security, limited token access, and input validation.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">5. Data Retention and Deletion</h2>
            <p>We retain your personal information only for as long as necessary to fulfill the purposes outlined in this policy. You may request deletion of your data at any time.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">6. Contact Us</h2>
            <p>If you have questions about this Privacy Policy, please contact us.</p>
            <div className="mt-2 space-y-1">
              <p><strong className="text-white">Business Name:</strong> Wandi AI</p>
              <p><strong className="text-white">Email:</strong> <a href="mailto:gayahaelyon@gmail.com" className="text-purple-400 hover:text-purple-300 underline">gayahaelyon@gmail.com</a></p>
            </div>
          </section>
        </div>

        <div className="mt-8 pt-6 border-t border-slate-700 text-center">
          <p className="text-slate-500 text-sm">Wandi AI &mdash; Instagram Scheduling Platform</p>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
