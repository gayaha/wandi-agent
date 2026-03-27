const TermsOfService = () => {
  return (
    <div className="min-h-screen bg-slate-900 py-12 px-4" dir="ltr">
      <div className="max-w-3xl mx-auto bg-slate-800/50 backdrop-blur-sm border border-slate-700 rounded-xl p-8">
        <h1 className="text-3xl font-bold text-white mb-2">WANDI AI Terms of Service</h1>
        <p className="text-slate-400 text-sm mb-8">Effective Date: March 4, 2026</p>

        <div className="space-y-8 text-slate-300 leading-relaxed">
          <section>
            <p>
              Welcome to WANDI AI. These Terms of Service govern your access to and use of the WANDI AI application and all related automation and content creation services.
            </p>
            <p className="mt-2">
              By accessing or using our Services, you agree to be bound by these Terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">1. Description of the Service</h2>
            <p>
              WANDI AI provides automated content creation, scheduling and publishing services intended for business owners and marketers. Our application integrates with Meta platforms through the official Graph API.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">2. Meta Platform Compliance</h2>
            <p>
              Our Services operate by connecting to your Meta accounts. By using WANDI AI, you confirm and agree that you must strictly comply with Meta's Terms of Service, Community Standards, and all relevant developer and platform policies.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">3. User Responsibility</h2>
            <p>
              You are solely responsible for all content that you create, schedule or publish through WANDI AI. We are not responsible for any content removal, account suspension, or bans imposed by Meta.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">4. Intellectual Property</h2>
            <p>
              The original brand assets and raw inputs you provide remain your property. By using WANDI AI, you grant us a non-exclusive, royalty-free license to use generated output for promotional and system improvement purposes.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">5. Termination</h2>
            <p>
              WANDI AI reserves the right to suspend or terminate your access at our sole discretion, without prior notice, for abuse, spam, violations of these Terms, or Meta's platform policies.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">6. Limitation of Liability</h2>
            <p>
              To the maximum extent permitted by law, WANDI AI shall not be liable for any indirect, incidental, special, consequential or punitive damages arising from your use of the Services.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">7. Governing Law</h2>
            <p>
              These Terms shall be governed by and construed in accordance with the laws of the State of Israel. Any legal proceedings shall be brought exclusively before courts in Tel Aviv, Israel.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-white mb-2">8. Contact Us</h2>
            <p>If you have any questions regarding these Terms, please contact us:</p>
            <div className="mt-2 space-y-1">
              <p><strong className="text-white">WANDI AI</strong></p>
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

export default TermsOfService;
