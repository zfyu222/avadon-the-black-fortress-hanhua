using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;

internal static class EnhancementSettings
{
    private static readonly string Root = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);

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
        using (var process = Process.Start(start))
        {
            Task<string> output = process.StandardOutput.ReadToEndAsync();
            Task<string> error = process.StandardError.ReadToEndAsync();
            process.WaitForExit();
            if (process.ExitCode != 0)
            {
                string details = error.Result.Trim();
                if (details.Length == 0) details = output.Result.Trim();
                throw new InvalidOperationException(details.Length == 0 ? "设置操作失败。" : details);
            }
        }
    }

    [STAThread]
    private static int Main(string[] args)
    {
#if SETTINGS_TEST
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
        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);
        if (!File.Exists(Path.Combine(Root, "Avadon.exe")))
        {
            MessageBox.Show("请把增强补丁解压到 Avadon.exe 所在文件夹，再打开增强设置。", "阿瓦登增强设置");
            return 1;
        }
        bool firstInstance;
        using (var mutex = new Mutex(true, "Local\\AvadonEnhancementSettings", out firstInstance))
        {
            if (firstInstance) Application.Run(new SettingsForm());
            else MessageBox.Show("增强设置窗口已打开。", "阿瓦登增强设置");
        }
        return 0;
    }

    private sealed class SettingsForm : Form
    {
        private readonly NumericUpDown fontScale = NumberField();
        private readonly NumericUpDown movement = NumberField();
        private readonly CheckBox follow = Toggle("镜头跟随角色");
        private readonly CheckBox inventory = Toggle("再按一次背包快捷键关闭背包");
        private readonly CheckBox fitLabels = Toggle("长标签自动缩小字号");
        private readonly CheckBox highlight = Toggle("按住 Shift 高亮可交互物");
        private readonly Label status = new Label { AutoSize = true, MaximumSize = new Size(460, 0) };
        private readonly Button save = new Button { Text = "保存并应用", AutoSize = true };
        private readonly Button restore = new Button { Text = "还原增强补丁", AutoSize = true };
        private readonly TableLayoutPanel panel = new TableLayoutPanel();
        private bool busy;

        public SettingsForm()
        {
            Text = "阿瓦登增强设置";
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
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 325));
            panel.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 125));
            Controls.Add(panel);

            AddFull(new Label { Text = "阿瓦登增强设置", Font = new Font(Font.FontFamily, 18, FontStyle.Bold), AutoSize = true }, 0);
            AddFull(new Label { Text = "退出游戏后保存，下次启动游戏时生效。", AutoSize = true }, 1);
            AddNumber("字体大小（%）", fontScale, 2);
            AddNumber("主角探索移动速度（%）", movement, 3);
            AddFull(fitLabels, 4);
            AddFull(follow, 5);
            AddFull(inventory, 6);
            AddFull(highlight, 7);
            AddFull(status, 8);
            var buttons = new FlowLayoutPanel { AutoSize = true, FlowDirection = FlowDirection.RightToLeft, Dock = DockStyle.Fill };
            buttons.Controls.Add(save);
            buttons.Controls.Add(restore);
            AddFull(buttons, 9);
            AcceptButton = save;
            LoadSettings();
            save.Click += async (sender, e) => await Apply(
                String.Format("-Action settings -Scale {0} -Speed {1} -Follow {2} -Inventory {3} -FitLabels {4} -Highlight {5}",
                    (int)fontScale.Value, (int)movement.Value, Flag(follow), Flag(inventory), Flag(fitLabels), Flag(highlight)), false);
            restore.Click += async (sender, e) =>
            {
                if (MessageBox.Show(this, "还原会移除增强功能并恢复安装前的设置。要继续吗？", Text,
                    MessageBoxButtons.OKCancel, MessageBoxIcon.Question) == DialogResult.OK)
                    await Apply("-Action uninstall", true);
            };
            FormClosing += (sender, e) => { if (busy) e.Cancel = true; };
        }

        private static NumericUpDown NumberField()
        {
            return new NumericUpDown { Minimum = 100, Maximum = 200, Increment = 1, Width = 95, TextAlign = HorizontalAlignment.Right };
        }

        private static CheckBox Toggle(string text) { return new CheckBox { Text = text, AutoSize = true }; }
        private static int Flag(CheckBox check) { return check.Checked ? 1 : 0; }
        private static int Percent(int value) { return Math.Max(100, Math.Min(200, value)); }

        private void AddFull(Control control, int row)
        {
            control.Margin = new Padding(3, 5, 3, 5);
            panel.Controls.Add(control, 0, row);
            panel.SetColumnSpan(control, 2);
        }

        private void AddNumber(string text, NumericUpDown field, int row)
        {
            panel.Controls.Add(new Label { Text = text, AutoSize = true, Anchor = AnchorStyles.Left }, 0, row);
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
            status.Text = restoring ? "正在还原…" : "正在保存…";
            try
            {
                await Task.Run(() => RunInstaller(arguments));
                LoadSettings();
                status.Text = restoring ? "已还原增强补丁。" : "已保存。启动游戏即可生效。";
            }
            catch (Exception error)
            {
                status.Text = "操作失败，请查看提示。";
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
