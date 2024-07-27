## Kaggle Notebook Backup 📚

This Python script automates downloading your Kaggle notebooks, including private ones (if desired), and creates a compressed archive for easy backup or transfer.

### **Local Installation:**

1. **Prerequisites:**
    - Python 3.x
    - `kaggle` and other packages: Install with `pip install -r requirements.txt`
    - Set up the Kaggle CLI according to the [official documentation](https://www.kaggle.com/docs/api)
2. **Download the repo:**

    ```bash
    git clone https://github.com/maxisoft/kaggle-notebook-backup.git
    ```

3. **Run the script:**

    ```bash
    python main.py [OPTIONS]
    ```

#### Options:

* `-o, --output` (default: `./kernels.zip`): Name and location of the output archive.
* `-p, --include-private` (default: `True`): Include private notebooks in the backup.
* `-u, --user` (default: `current user`): Kaggle username whose notebooks to download.
* `-t, --tmp-dir` (default: `temporary directory`): Path to a custom temporary directory.

#### Default Behavior:

The default execution will create an archive named `kernels.zip` with all your Kaggle kernels in the *current directory*.

### Running via GitHub Actions Workflow 🚀

This repository also includes a GitHub Actions workflow named `doit.yml` that can be used to automate the script execution on a schedule or upon pushes to the `main` branch.
To enable this functionality, you'll need to configure secrets within your repository settings.

**Here's a breakdown of the steps involved:**

1. **Fork this Repository:** Create your own fork of this repository on GitHub.
2. **Navigate to Actions:** Go to your forked repository's settings and then to the "Actions" tab.
3. **Enable the `doit.yml` Workflow:** Find the `doit.yml` workflow and enable it to run on pushes or schedules.
4. **Set Up Secrets (Required):**

    - Navigate to your repository's settings and then to "Secrets."
    - Create two secrets:
        - `KAGGLE_USERNAME`: Your Kaggle username.
        - `KAGGLE_KEY`: Your Kaggle API key (obtainable from your profile settings).
5. **Manual Trigger:**  
You can manually trigger the workflow by navigating to the “Actions” tab in your repository, selecting the `doit.yml` workflow, and clicking the “Run workflow” button.
6. **Output as GitHub Artifact:**
    - The resulting zip file (`kernels.zip`) will be uploaded as a GitHub artifact, making it easy to download and access from the Actions tab.

**Important Note:**

- **Security:** Never store your API key directly in the code. Using GitHub secrets ensures secure handling of sensitive information.

**Benefits of Using GitHub Actions:**

- **Automated Execution:** The script runs automatically based on your chosen schedule, upon code pushes, or manually.
- **Regular Backups:** Scheduled execution helps maintain updated backups of your notebooks.
- **Reduced Manual Work:** Frees you from manually running the script, saving time and effort.

By following these steps and leveraging GitHub Actions, you can automate the process of backing up your Kaggle notebooks, ensuring a more streamlined and safe workflow.

### Contributing:

Feel free to contribute bug fixes, improvements, or feature requests. Fork the repository, create a pull request, and share your changes! 🚀
