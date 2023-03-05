using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices.WindowsRuntime;
using Windows.Foundation;
using Windows.Foundation.Collections;
using Windows.Storage;
using Windows.Storage.Pickers;
using Windows.Storage.Pickers.Provider;
using Windows.UI.Xaml;
using Windows.UI.Xaml.Controls;
using Windows.UI.Xaml.Controls.Primitives;
using Windows.UI.Xaml.Data;
using Windows.UI.Xaml.Input;
using Windows.UI.Xaml.Media;
using Windows.UI.Xaml.Navigation;
using Windows.System;
using Windows.UI.Popups;

namespace OS_Project
{
    /// <summary>
    /// An empty page that can be used on its own or navigated to within a Frame.
    /// </summary>
    public sealed partial class MainPage : Page
    {
        private StorageFolder folder;
        public MainPage()
        {
            this.InitializeComponent();
            
        }

        private async void PopupMessage(string msg)
        {
            MessageDialog dialog = new MessageDialog(msg, "Message");
            dialog.Commands.Add(new UICommand("OK") { Id = 0 });
            dialog.Commands.Add(new UICommand("Cancel") { Id = 1 });
            dialog.DefaultCommandIndex = 1;
            //dialog.CancelCommandIndex = 1;
            await dialog.ShowAsync();
        }

        private async void FolderPick(object sender, RoutedEventArgs e)
        {
            FolderPicker folderPicker = new FolderPicker();
            folderPicker.SuggestedStartLocation = PickerLocationId.ComputerFolder;
            folderPicker.FileTypeFilter.Add("*");

            folder = await folderPicker.PickSingleFolderAsync();
            Folder.Text = folder.Path;
            if (!folder.Path.EndsWith(":\\") || !folder.IsOfType(StorageItemTypes.Folder))
                PopupMessage("Please choose a disk to continue!!!");
        }
    }
}
