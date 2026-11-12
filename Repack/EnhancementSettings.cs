using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Globalization;
using Microsoft.Win32;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

internal static class EnhancementSettings
{
    private static readonly string Root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);

    private const string PreferencesKey = @"HKEY_CURRENT_USER\Software\AvadonEnhancementSettings";
    private static bool english;
    private static string TextFor(string chinese, string translation) { return english ? translation : chinese; }
    private static string Title { get { return TextFor("阿瓦登增强设置", "Avadon Enhancement Settings"); } }

    private static bool UseEnglish(int preference, CultureInfo systemLanguage)
    {
        return preference == 2 || (preference != 1 && systemLanguage.TwoLetterISOLanguageName != "zh");
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode)]
    private static extern uint GetPrivateProfileInt(string section, string key, int fallback, string file);

    private static int ReadSetting(string file, string section, string key, int fallback)
    {
        return unchecked((int)GetPrivateProfileInt(section, key, fallback, Path.Combine(Root, "AvadonChinese", file)));
    }

    private static void RunInstaller(string arguments)
    {
        string powershell = Path.Combine(Environment.SystemDirectory, "WindowsPowerShell", "v1.0", "powershell.exe");
        string script = Path.Combine(Root, "字体增强.ps1");
        var start = new ProcessStartInfo(powershell,
            "-NoProfile -NonInteractive -ExecutionPolicy Bypass -File \"" + script + "\" -GameRoot \"" + Root + "\" " + arguments)
        {
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            StandardOutputEncoding = Encoding.UTF8,
            StandardErrorEncoding = Encoding.UTF8
        };
        start.EnvironmentVariables["AVADON_SETTINGS_UTF8"] = "1";
        start.EnvironmentVariables["AVADON_SETTINGS_LANGUAGE"] = english ? "en" : "zh";
        using (var process = Process.Start(start))
        {
            Task<string> output = process.StandardOutput.ReadToEndAsync();
            Task<string> error = process.StandardError.ReadToEndAsync();
            process.WaitForExit();
            if (process.ExitCode != 0)
            {
                string details = error.Result.Trim();
                if (details.Length == 0) details = output.Result.Trim();
                throw new InvalidOperationException(details.Length == 0 ? TextFor("设置操作失败。", "The settings operation failed.") : details);
            }
        }
    }

    [STAThread]
    private static int Main(string[] args)
    {
#if SETTINGS_TEST
        if (args.Length == 1 && args[0] == "--verify-language")
        {
            var en = CultureInfo.GetCultureInfo("en-US");
            var zh = CultureInfo.GetCultureInfo("zh-CN");
            if (!UseEnglish(0, en) || UseEnglish(0, zh) || UseEnglish(1, en) || !UseEnglish(2, zh)) return 1;
            using (var form = new SettingsForm(1))
                return form.VerifyLanguageSwitch() ? 0 : 1;
        }
        if (args.Length == 1 && args[0] == "--verify-save")
        {
            RunInstaller("-Action settings -Scale 137 -Speed 200 -Follow 0 -Inventory 0 -FitLabels 0 -Highlight 0");
            return ReadSetting("font.ini", "Font", "ScalePercent", 0) == 137 &&
                ReadSetting("font.ini", "Font", "FitLabels", 1) == 0 &&
                ReadSetting("camera.ini", "Movement", "SpeedPercent", 0) == 200 &&
                ReadSetting("camera.ini", "Camera", "FollowCharacter", 1) == 0 &&
                ReadSetting("camera.ini", "Inventory", "ToggleHotkey", 1) == 0 &&
                ReadSetting("camera.ini", "Interaction", "HighlightOnShift", 1) == 0 ? 0 : 1;
        }
#endif
        int preference = (int?)Registry.GetValue(PreferencesKey, "Language", 0) ?? 0;
        if (preference < 0 || preference > 2) preference = 0;
        english = UseEnglish(preference, CultureInfo.CurrentUICulture);
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        if (!File.Exists(Path.Combine(Root, "Avadon.exe")))
        {
            MessageBox.Show(TextFor("请把增强补丁解压到 Avadon.exe 所在文件夹，再打开增强设置。",
                "Extract the enhancement patch into the folder containing Avadon.exe, then reopen Settings."), Title);
            return 1;
        }
        bool firstInstance;
        using (var mutex = new Mutex(true, "Local\\AvadonEnhancementSettings", out firstInstance))
        {
            if (firstInstance) Application.Run(new SettingsForm(preference));
            else MessageBox.Show(TextFor("增强设置窗口已打开。", "The settings window is already open."), Title);
        }
        return 0;
    }

    private sealed class SettingsForm : Form
    {
        private readonly NumericUpDown fontScale = NumberField();
        private readonly NumericUpDown movement = NumberField();
        private readonly CheckBox follow = new CheckBox { AutoSize = true };
        private readonly CheckBox inventory = new CheckBox { AutoSize = true };
        private readonly CheckBox fitLabels = new CheckBox { AutoSize = true };
        private readonly CheckBox highlight = new CheckBox { AutoSize = true };
        private readonly Label status = new Label { AutoSize = true, MaximumSize = new Size(475, 0) };
        private readonly Button save = new Button { AutoSize = true };
        private readonly Button restore = new Button { AutoSize = true };
        private readonly TableLayoutPanel panel = new TableLayoutPanel();
        private readonly Label heading = new Label { AutoSize = true };
        private readonly Label instruction = new Label { AutoSize = true };
        private readonly Label fontLabel = new Label { AutoSize = true, Anchor = AnchorStyles.Left };
        private readonly Label speedLabel = new Label { AutoSize = true, Anchor = AnchorStyles.Left };
        private readonly Label languageLabel = new Label { AutoSize = true, Anchor = AnchorStyles.Left };
        private readonly ComboBox language = new ComboBox { DropDownStyle = ComboBoxStyle.DropDownList, Width = 120 };
        private bool busy;

        public SettingsForm(int preference)
        {
            Font = new Font("Microsoft YaHei UI", 10);
            AutoScaleMode = AutoScaleMode.Font;
            AutoSize = true;
            AutoSizeMode = AutoSizeMode.GrowAndShrink;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            MaximizeBox = false;
            StartPosition = FormStartPosition.CenterScreen;
            BackColor = Color.FromArgb(246, 248, 252);
            ForeColor = Color.FromArgb(29, 43, 63);
            panel.Padding = new Padding(24, 18, 24, 18);
            panel.AutoSize = true;
            panel.Dock = DockStyle.Fill;
            panel.ColumnCount = 2;
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 350));
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 125));
            Controls.Add(panel);

            heading.Font = new Font(Font.FontFamily, 18, FontStyle.Bold);
            AddFull(heading, 0);
            AddFull(instruction, 1);
            AddField(languageLabel, language, 2);
            AddField(fontLabel, fontScale, 3);
            AddField(speedLabel, movement, 4);
            AddFull(fitLabels, 5);
            AddFull(follow, 6);
            AddFull(inventory, 7);
            AddFull(highlight, 8);
            AddFull(status, 9);
            language.Items.AddRange(new object[] { "System / 系统", "简体中文", "English" });
            language.SelectedIndex = preference;
            RefreshLanguage(preference);
            language.SelectedIndexChanged += (sender, e) =>
            {
                RefreshLanguage(language.SelectedIndex);
                status.Text = "";
                try
                {
                    Registry.SetValue(PreferencesKey, "Language", language.SelectedIndex, RegistryValueKind.DWord);
                }
                catch (Exception error)
                {
                    if (!(error is UnauthorizedAccessException || error is System.Security.SecurityException || error is IOException)) throw;
                    status.Text = TextFor("本次已切换语言，无法保存语言偏好。", "Language changed for this session. The preference could not be saved.");
                }
            };
            var buttons = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.RightToLeft, Dock = DockStyle.Fill };
            buttons.Controls.Add(save);
            buttons.Controls.Add(restore);
            AddFull(buttons, 10);
            AcceptButton = save;
            LoadSettings();
            save.Click += async (sender, e) => await Apply(
                String.Format("-Action settings -Scale {0} -Speed {1} -Follow {2} -Inventory {3} -FitLabels {4} -Highlight {5}",
                    (int)fontScale.Value, (int)movement.Value, Flag(follow), Flag(inventory), Flag(fitLabels), Flag(highlight)), false);
            restore.Click += async (sender, e) =>
            {
                if (MessageBox.Show(this, TextFor("还原会移除增强功能并恢复安装前的设置。要继续吗？",
                    "Restore the settings and plugin from before the enhancement patch was installed?"), Text,
                    MessageBoxButtons.OKCancel, MessageBoxIcon.Question) == DialogResult.OK)
                    await Apply("-Action uninstall", true);
            };
            FormClosing += (sender, e) => { if (busy) e.Cancel = true; };
        }

        private static NumericUpDown NumberField()
        {
            return new NumericUpDown { Minimum = 100, Maximum = 200, Increment = 1, Width = 95, TextAlign = HorizontalAlignment.Right };
        }

        private void RefreshLanguage(int preference)
        {
            english = UseEnglish(preference, CultureInfo.CurrentUICulture);
            Text = heading.Text = Title;
            instruction.Text = TextFor("退出游戏后保存，下次启动游戏时生效。", "Close the game before saving. Changes apply on the next launch.");
            languageLabel.Text = TextFor("界面语言", "Display language");
            fontLabel.Text = TextFor("字体大小（%）", "Font size (%)");
            speedLabel.Text = TextFor("主角探索移动速度（%）", "Player movement speed outside combat (%)");
            fitLabels.Text = TextFor("长标签自动缩小字号", "Shrink long labels to fit");
            follow.Text = TextFor("镜头跟随角色", "Follow the player with the camera");
            inventory.Text = TextFor("再按一次背包快捷键关闭背包", "Press the inventory shortcut again to close it");
            highlight.Text = TextFor("按住 Shift 标记画面内可交互物", "Hold Shift to mark on-screen interactable objects");
            save.Text = TextFor("保存并应用", "Save and Apply");
            restore.Text = TextFor("还原增强补丁", "Restore Original Settings");
        }

#if SETTINGS_TEST
        public bool VerifyLanguageSwitch()
        {
            if (Text != "阿瓦登增强设置") return false;
            // Test the same refresh without writing to the user's registry.
            RefreshLanguage(2);
            if (Text != "Avadon Enhancement Settings" || save.Text != "Save and Apply") return false;
            RefreshLanguage(1);
            return fontLabel.Text == "字体大小（%）";
        }
#endif
        private static int Flag(CheckBox check) { return check.Checked ? 1 : 0; }
        private static int Percent(int value) { return Math.Max(100, Math.Min(200, value)); }

        private void AddFull(Control control, int row)
        {
            control.Margin = new Padding(3, 5, 3, 5);
            panel.Controls.Add(control, 0, row);
            panel.SetColumnSpan(control, 2);
        }

        private void AddField(Label label, Control field, int row)
        {
            panel.Controls.Add(label, 0, row);
            panel.Controls.Add(field, 1, row);
        }

        private void LoadSettings()
        {
            fontScale.Value = Percent(ReadSetting("font.ini", "Font", "ScalePercent", 150));
            movement.Value = Percent(ReadSetting("camera.ini", "Movement", "SpeedPercent", 100));
            fitLabels.Checked = ReadSetting("font.ini", "Font", "FitLabels", 1) != 0;
            follow.Checked = ReadSetting("camera.ini", "Camera", "FollowCharacter", 1) != 0;
            highlight.Checked = ReadSetting("camera.ini", "Interaction", "HighlightOnShift", 1) != 0;
            inventory.Checked = ReadSetting("camera.ini", "Inventory", "ToggleHotkey", 1) != 0;
        }

        private async Task Apply(string arguments, bool restoring)
        {
            busy = true;
            panel.Enabled = false;
            status.Text = restoring ? TextFor("正在还原…", "Restoring…") : TextFor("正在保存…", "Saving…");
            try
            {
                await Task.Run(() => RunInstaller(arguments));
                LoadSettings();
                status.Text = restoring ? TextFor("已还原增强补丁。", "Enhancements removed.") : TextFor("已保存。启动游戏即可生效。", "Saved. Changes apply when you launch the game.");
            }
            catch (Exception error)
            {
                status.Text = TextFor("操作失败，请查看提示。", "The operation failed. See the error message.");
                MessageBox.Show(this, error.Message, Text, MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                busy = false;
                panel.Enabled = true;
            }
        }
    }
}
