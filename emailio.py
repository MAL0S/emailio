import os
import json
import threading
import smtplib
from email.message import EmailMessage
import requests
import customtkinter as ctk

# Application Appearance Configuration
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

CONFIG_FILE = "config.json"

class EmailAutomatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # --- Window Setup ---
        self.title("Email Automator")
        self.geometry("700x580")
        self.minsize(600, 500)
        self.configure(fg_color="#0a0a0a")  # Matte dark background matching asset

        # --- Persistent Settings ---
        self.config = {
            "mode": "resend",  # 'resend' or 'smtp'
            "resend_api_key": "",
            "resend_audience_id": "",
            "smtp_provider": "Gmail",
            "smtp_email": "",
            "smtp_password": ""
        }
        self.load_config()

        # Track active checkboxes: {email_str: (checkbox_widget, BooleanVar)}
        self.checkbox_data = {}

        # --- UI Initialization ---
        self._build_header()
        self._build_input_bar()
        self._build_email_list_container()

        # Fetch emails on startup if API key exists
        if self.config.get("resend_api_key") and self.config.get("resend_audience_id"):
            self.refresh_emails_async()

    # -------------------------------------------------------------------
    # Configuration Storage
    # -------------------------------------------------------------------
    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    self.config.update(json.load(f))
            except Exception as e:
                print(f"Failed to load config: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Failed to save config: {e}")

    # -------------------------------------------------------------------
    # UI Layout Construction
    # -------------------------------------------------------------------
    def _build_header(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=35, pady=(25, 10))

        # Avatar / Account Button
        self.avatar_btn = ctk.CTkButton(
            self.header_frame,
            text="👤",
            width=48,
            height=48,
            corner_radius=24,
            fg_color="#ffffff",
            text_color="#000000",
            hover_color="#e0e0e0",
            font=("Arial", 20)
        )
        self.avatar_btn.pack(side="left")

        # Status Label
        self.status_label = ctk.CTkLabel(
            self.header_frame,
            text="Ready",
            text_color="#888888",
            font=("Arial", 12)
        )
        self.status_label.pack(side="left", padx=15)

        # APIs / Settings Nav Button
        self.api_btn = ctk.CTkButton(
            self.header_frame,
            text="apis >",
            fg_color="transparent",
            hover_color="#181818",
            text_color="#ffffff",
            font=("Arial", 18, "bold"),
            command=self.open_settings_modal
        )
        self.api_btn.pack(side="right")

    def _build_input_bar(self):
        # Oval Input Container matching the mock mockup
        self.input_container = ctk.CTkFrame(
            self,
            fg_color="transparent",
            border_width=2,
            border_color="#ffffff",
            corner_radius=30
        )
        self.input_container.pack(pady=30, padx=40, ipady=3, ipadx=5)

        self.msg_entry = ctk.CTkEntry(
            self.input_container,
            placeholder_text="type something....",
            placeholder_text_color="#666666",
            width=380,
            fg_color="transparent",
            border_width=0,
            text_color="#ffffff",
            font=("Arial", 16)
        )
        self.msg_entry.pack(side="left", padx=(20, 10), pady=8)

        # Send Play Button
        self.send_btn = ctk.CTkButton(
            self.input_container,
            text="▶",
            width=40,
            height=40,
            corner_radius=20,
            fg_color="#1a73e8",
            hover_color="#1557b0",
            text_color="#ffffff",
            font=("Arial", 14),
            command=self.send_mass_email_async
        )
        self.send_btn.pack(side="right", padx=(5, 10))

    def _build_email_list_container(self):
        # Scrollable container for email checkboxes
        self.scroll_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            width=480,
            height=260,
            scrollbar_button_color="#222222",
            scrollbar_button_hover_color="#444444"
        )
        self.scroll_frame.pack(anchor="center", pady=(10, 20))

        # Bottom horizontal divider
        self.divider = ctk.CTkFrame(self, height=1, fg_color="#333333")
        self.divider.pack(fill="x", padx=100, pady=(0, 20))

    # -------------------------------------------------------------------
    # List Rendering & Management
    # -------------------------------------------------------------------
    def render_email_list(self, emails):
        # Clear existing entries
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        self.checkbox_data.clear()

        if not emails:
            no_data_label = ctk.CTkLabel(
                self.scroll_frame,
                text="No emails found. Configure API key or fetch users.",
                text_color="#666666",
                font=("Arial", 14)
            )
            no_data_label.pack(pady=30)
            return

        for idx, email in enumerate(emails):
            var = ctk.BooleanVar(value=True)  # Default all checked

            # Match mockup: last email item in mockup was deselected
            if idx == len(emails) - 1 and len(emails) > 1:
                var.set(False)

            cb = ctk.CTkCheckBox(
                self.scroll_frame,
                text=email,
                variable=var,
                text_color="#ffffff",
                font=("Arial", 16),
                fg_color="#1a73e8",
                hover_color="#1557b0",
                border_color="#555555",
                corner_radius=8,
                checkbox_width=22,
                checkbox_height=22
            )
            cb.pack(anchor="w", pady=8, padx=20)
            self.checkbox_data[email] = var

    # -------------------------------------------------------------------
    # Resend API & Data Fetching Logic
    # -------------------------------------------------------------------
    def refresh_emails_async(self):
        self.status_label.configure(text="Fetching emails...", text_color="#1a73e8")
        threading.Thread(target=self._fetch_emails_worker, daemon=True).start()

    def _fetch_emails_worker(self):
        api_key = self.config.get("resend_api_key")
        audience_id = self.config.get("resend_audience_id")

        if not api_key or not audience_id:
            self.after(0, self._handle_fetch_result, [], "Missing API Configuration")
            return

        url = f"https://api.resend.com/audiences/{audience_id}/contacts"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200:
                contacts = res.json().get("data", [])
                # Extract activated / active subscribers
                active_emails = [c["email"] for c in contacts if not c.get("unsubscribed", False)]
                self.after(0, self._handle_fetch_result, active_emails, "Emails synced from Resend")
            else:
                err_msg = f"API Error ({res.status_code})"
                self.after(0, self._handle_fetch_result, [], err_msg)
        except Exception as e:
            self.after(0, self._handle_fetch_result, [], f"Connection error: {e}")

    def _handle_fetch_result(self, emails, status):
        self.render_email_list(emails)
        self.status_label.configure(text=status, text_color="#00ff66" if emails else "#ff4444")

    # -------------------------------------------------------------------
    # Sending Logic (Resend API or SMTP)
    # -------------------------------------------------------------------
    def send_mass_email_async(self):
        message = self.msg_entry.get().strip()
        selected_emails = [email for email, var in self.checkbox_data.items() if var.get()]

        if not message:
            self.status_label.configure(text="Message cannot be empty", text_color="#ff4444")
            return

        if not selected_emails:
            self.status_label.configure(text="No recipients selected", text_color="#ff4444")
            return

        self.send_btn.configure(state="disabled")
        self.status_label.configure(text=f"Sending to {len(selected_emails)} recipient(s)...", text_color="#1a73e8")

        threading.Thread(
            target=self._send_worker,
            args=(message, selected_emails),
            daemon=True
        ).start()

    def _send_worker(self, message, recipients):
        mode = self.config.get("mode", "resend")
        success = False
        status_msg = ""

        if mode == "resend":
            success, status_msg = self._send_via_resend(message, recipients)
        else:
            success, status_msg = self._send_via_smtp(message, recipients)

        self.after(0, self._handle_send_result, success, status_msg)

    def _send_via_resend(self, message, recipients):
        api_key = self.config.get("resend_api_key")
        if not api_key:
            return False, "Resend API key missing!"

        url = "https://api.resend.com/emails/batch"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        # Build Batch Payload
        payload = [
            {
                "from": "Notification <onboarding@resend.dev>",  # Replace with verified custom domain
                "to": [email],
                "subject": "Automated Update",
                "text": message
            }
            for email in recipients
        ]

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=15)
            if res.status_code in (200, 201):
                return True, f"Sent batch to {len(recipients)} addresses!"
            else:
                return False, f"Resend Error: {res.status_code}"
        except Exception as e:
            return False, f"Resend request failed: {e}"

    def _send_via_smtp(self, message, recipients):
        provider = self.config.get("smtp_provider", "Gmail")
        sender_email = self.config.get("smtp_email")
        sender_pwd = self.config.get("smtp_password")

        smtp_hosts = {
            "Gmail": ("smtp.gmail.com", 587),
            "iCloud": ("smtp.mail.me.com", 587),
            "Hotmail/Outlook": ("smtp-mail.outlook.com", 587)
        }

        host, port = smtp_hosts.get(provider, ("smtp.gmail.com", 587))

        if not sender_email or not sender_pwd:
            return False, "SMTP Credentials incomplete!"

        try:
            with smtplib.SMTP(host, port, timeout=15) as server:
                server.starttls()
                server.login(sender_email, sender_pwd)

                for email in recipients:
                    msg = EmailMessage()
                    msg.set_content(message)
                    msg["Subject"] = "Update"
                    msg["From"] = sender_email
                    msg["To"] = email
                    server.send_message(msg)

            return True, f"Sent via {provider} to {len(recipients)} recipients!"
        except Exception as e:
            return False, f"SMTP Error: {e}"

    def _handle_send_result(self, success, status_msg):
        self.send_btn.configure(state="normal")
        if success:
            self.msg_entry.delete(0, "end")
            self.status_label.configure(text=status_msg, text_color="#00ff66")
        else:
            self.status_label.configure(text=status_msg, text_color="#ff4444")

    # -------------------------------------------------------------------
    # Settings / API Configuration Window
    # -------------------------------------------------------------------
    def open_settings_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("API & Account Setup")
        modal.geometry("450x520")
        modal.configure(fg_color="#121212")
        modal.transient(self)
        modal.grab_set()

        ctk.CTkLabel(
            modal, text="API & Account Configuration",
            font=("Arial", 18, "bold"), text_color="#ffffff"
        ).pack(pady=(20, 15))

        # Mode Selector
        mode_var = ctk.StringVar(value=self.config.get("mode", "resend"))

        def toggle_mode(value):
            if value == "resend":
                resend_frame.pack(fill="x", padx=20, pady=10)
                smtp_frame.pack_forget()
            else:
                smtp_frame.pack(fill="x", padx=20, pady=10)
                resend_frame.pack_forget()

        segmented_btn = ctk.CTkSegmentedButton(
            modal,
            values=["resend", "smtp"],
            variable=mode_var,
            command=toggle_mode,
            selected_color="#1a73e8"
        )
        segmented_btn.pack(pady=10)

        # --- Resend Sub-Frame ---
        resend_frame = ctk.CTkFrame(modal, fg_color="transparent")
        
        ctk.CTkLabel(resend_frame, text="Resend API Key", text_color="#aaaaaa").pack(anchor="w")
        resend_key_entry = ctk.CTkEntry(resend_frame, width=380, show="*")
        resend_key_entry.insert(0, self.config.get("resend_api_key", ""))
        resend_key_entry.pack(pady=(2, 10))

        ctk.CTkLabel(resend_frame, text="Audience / Segment ID", text_color="#aaaaaa").pack(anchor="w")
        resend_aud_entry = ctk.CTkEntry(resend_frame, width=380)
        resend_aud_entry.insert(0, self.config.get("resend_audience_id", ""))
        resend_aud_entry.pack(pady=(2, 10))

        # --- SMTP Sub-Frame ---
        smtp_frame = ctk.CTkFrame(modal, fg_color="transparent")

        ctk.CTkLabel(smtp_frame, text="Provider", text_color="#aaaaaa").pack(anchor="w")
        provider_menu = ctk.CTkOptionMenu(
            smtp_frame,
            values=["Gmail", "iCloud", "Hotmail/Outlook"],
            fg_color="#222222",
            button_color="#333333"
        )
        provider_menu.set(self.config.get("smtp_provider", "Gmail"))
        provider_menu.pack(pady=(2, 10), fill="x")

        ctk.CTkLabel(smtp_frame, text="Email Address", text_color="#aaaaaa").pack(anchor="w")
        smtp_email_entry = ctk.CTkEntry(smtp_frame, width=380)
        smtp_email_entry.insert(0, self.config.get("smtp_email", ""))
        smtp_email_entry.pack(pady=(2, 10))

        ctk.CTkLabel(smtp_frame, text="App Password", text_color="#aaaaaa").pack(anchor="w")
        smtp_pass_entry = ctk.CTkEntry(smtp_frame, width=380, show="*")
        smtp_pass_entry.insert(0, self.config.get("smtp_password", ""))
        smtp_pass_entry.pack(pady=(2, 10))

        # Initial view display based on current mode
        toggle_mode(mode_var.get())

        # Save Action
        def save_and_close():
            self.config["mode"] = mode_var.get()
            self.config["resend_api_key"] = resend_key_entry.get().strip()
            self.config["resend_audience_id"] = resend_aud_entry.get().strip()
            self.config["smtp_provider"] = provider_menu.get()
            self.config["smtp_email"] = smtp_email_entry.get().strip()
            self.config["smtp_password"] = smtp_pass_entry.get().strip()

            self.save_config()
            modal.destroy()

            # Trigger fresh email pull
            if self.config["mode"] == "resend":
                self.refresh_emails_async()

        ctk.CTkButton(
            modal,
            text="Save Settings",
            fg_color="#1a73e8",
            hover_color="#1557b0",
            command=save_and_close
        ).pack(side="bottom", pady=25)


if __name__ == "__main__":
    app = EmailAutomatorApp()
    app.mainloop()
