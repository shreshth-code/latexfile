import sys
import re
import os
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QListWidget, QListWidgetItem,
                            QCheckBox, QFileDialog, QMessageBox, QLabel, QProgressBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

class LatexParser:
    """Parse LaTeX file to extract components like sections, subsections, etc."""
    
    def __init__(self, file_path):
        self.file_path = file_path
        self.components = []
        self.full_content = ""
        
    def read_file(self):
        """Read LaTeX file content"""
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.full_content = f.read()
            return True
        except Exception as e:
            print(f"Error reading file: {e}")
            return False
            
    def extract_components(self):
        """Extract components from LaTeX file"""
        if not self.full_content:
            return False
            
        self.components = []
   
        component_patterns = [
          
            (r'\\documentclass\{([^}]+)\}', 'Document Class', True),
          
            (r'\\section\{([^}]+)\}((?:(?!\\section\{)[\s\S])*)', 'Section', False),
           
            (r'\\subsection\{([^}]+)\}((?:(?!\\section\{|\\subsection\{)[\s\S])*)', 'Subsection', False),
          
            (r'\\subsubsection\{([^}]+)\}((?:(?!\\section\{|\\subsection\{|\\subsubsection\{)[\s\S])*)', 'Subsubsection', False)
        ]
        
        doc_begin = self.full_content.find('\\begin{document}')
        doc_end = self.full_content.find('\\end{document}')
        
        if doc_begin == -1:
            doc_begin = 0
        if doc_end == -1:
            doc_end = len(self.full_content)
            
        document_content = self.full_content[doc_begin:doc_end]
        
        for pattern, comp_type, is_preamble in component_patterns:
        
            search_text = self.full_content[:doc_begin] if is_preamble else document_content
            
            matches = re.finditer(pattern, search_text, re.DOTALL)
            for i, match in enumerate(matches):
                try:
                    title = match.group(1).strip()
                    
                
                    if len(match.groups()) > 1:
                        content = match.group(0)  
                    else:
                        content = match.group(0)
                    
                   
                    title = re.sub(r'\s+', ' ', title).strip()
                    if len(title) > 50:
                        title = title[:47] + "..."
                    
                    
                    start = match.start() + (doc_begin if not is_preamble else 0)
                    end = match.end() + (doc_begin if not is_preamble else 0)
                    
                    self.components.append({
                        'type': comp_type,
                        'name': title,
                        'content': content,
                        'start': start,
                        'end': end,
                        'id': f"{comp_type}_{i+1}",
                        'is_preamble': is_preamble
                    })
                except Exception as e:
                    print(f"Error extracting component: {e}")
        
        
        self.components.sort(key=lambda x: x['start'])
        return True
    
    def find_component_end(self, start, comp_type):
        """Find the end of a component based on its type"""
        
        if comp_type in ['Document Class', 'Section', 'Subsection', 'Subsubsection']:
           
            next_command = self.full_content.find('\\', start + 1)
            next_newline = self.full_content.find('\n', start + 1)
            
            if next_command == -1:
                next_command = len(self.full_content)
            if next_newline == -1:
                next_newline = len(self.full_content)
                
            return min(next_command, next_newline) + 1
            
  
        elif comp_type in ['Figure', 'Table', 'Equation', 'Environment']:
           
            env_match = re.search(r'\\begin\{(.*?)\}', self.full_content[start:start+50])
            if env_match:
                env_name = env_match.group(1)
                end_pattern = f"\\end{{{env_name}}}"
                end_pos = self.full_content.find(end_pattern, start)
                if end_pos != -1:
                    return end_pos + len(end_pattern)
        
        return len(self.full_content)
    
    def _copy_images(self, content, output_dir):
        """Copy images referenced in the LaTeX content to the output directory"""
       
        image_patterns = [
            r'\\includegraphics(?:\[.*?\])?\{(.*?)\}',  
            r'\\graphicspath\{(.*?)\}',                 
            r'\\figure\{(.*?)\}'                        
        ]
        
        modified_content = content
        for pattern in image_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                img_path = match.group(1)
                if img_path:
                    
                    if os.path.isabs(img_path):
                        original_path = img_path
                    else:
                        original_path = os.path.join(os.path.dirname(self.file_path), img_path)
                    
                    try:
                        if os.path.exists(original_path):
                           
                            images_dir = os.path.join(output_dir, 'images')
                            os.makedirs(images_dir, exist_ok=True)
                            
                            img_filename = os.path.basename(original_path)
                            new_path = os.path.join(images_dir, img_filename)
                            import shutil
                            shutil.copy2(original_path, new_path)
                            
                            rel_path = os.path.join('images', img_filename)
                            if '\\includegraphics' in match.group(0):
                                old_cmd = match.group(0)
                                new_cmd = f'\\includegraphics[width=\\textwidth]{{{rel_path}}}'
                                modified_content = modified_content.replace(old_cmd, new_cmd)
                            else:
                                modified_content = modified_content.replace(img_path, rel_path)
                    except Exception as e:
                        print(f"Error copying image {img_path}: {e}")
        
        return modified_content

    def generate_custom_tex(self, selected_components, output_file):
        """Generate a new TeX file with only selected components"""
        try:
            
            doc_begin = self.full_content.find('\\begin{document}')
            if doc_begin == -1:
                return False
                
            preamble = self.full_content[:doc_begin].rstrip()
            
            
            new_content = []
            
          
            new_content.append(preamble)
            
          
            if '\\usepackage{graphicx}' not in preamble:
                new_content.append('\\usepackage[final]{graphicx}') 
            else:
          
                preamble = re.sub(
                    r'\\usepackage\[.*?draft.*?\]{graphicx}',
                    r'\\usepackage[final]{graphicx}',
                    preamble
                )
            
           
            if '\\documentclass[' in preamble:
                preamble = re.sub(
                    r'\\documentclass\[(.*?)draft(.*?)\]',
                    r'\\documentclass[\1final\2]',
                    preamble
                )
            
            output_dir = os.path.dirname(output_file)
            os.makedirs(output_dir, exist_ok=True)
            
            new_content.append('\\begin{document}')
            
            selected_ids = set(comp['id'] for comp in selected_components)
            for component in self.components:
                if component['id'] in selected_ids and not component['is_preamble']:
                    processed_content = self._copy_images(component['content'].strip(), output_dir)
                    new_content.append('\n' + processed_content)
            
            
            new_content.append('\n\\end{document}\n')
            
           
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(new_content))
                return True
            except Exception as e:
                print(f"Error writing new TeX file: {e}")
                return False
                
        except Exception as e:
            print(f"Error generating custom TeX file: {e}")
            return False


class CompilationThread(QThread):
    """Thread for compiling LaTeX to PDF"""
    update_status = pyqtSignal(str)
    update_progress = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, tex_file, output_dir):
        super().__init__()
        self.tex_file = tex_file
        self.output_dir = output_dir
        self.log_file = None
        
    def _check_log_for_errors(self, log_content):
        """Parse log file for common LaTeX errors"""
        error_patterns = [
            (r'! LaTeX Error: (.*?)\n', 'LaTeX Error'),
            (r'! Package (.*?) Error: (.*?)\n', 'Package Error'),
            (r'! Missing (.*?)\n', 'Missing Element'),
            (r'No file (.*?)\n', 'Missing File'),
            (r'! Undefined control sequence', 'Undefined Command'),
            (r'! Emergency stop', 'Emergency Stop')
        ]
        
        errors = []
        for pattern, error_type in error_patterns:
            matches = re.finditer(pattern, log_content, re.MULTILINE)
            for match in matches:
                errors.append(f"{error_type}: {match.group(1)}")
        
        return errors

    def _compile_latex(self):
        """Run LaTeX compilation with detailed error checking"""
        try:
            
            os.makedirs(self.output_dir, exist_ok=True)
            
          
            cmd = [
                'pdflatex',
                '-interaction=nonstopmode',
                '-file-line-error',
                '-halt-on-error',
                '-no-pdf',  
                f'-output-directory={self.output_dir}',
                self.tex_file
            ]
            
            self.update_status.emit("Running first compilation pass...")
            self.update_progress.emit(20)
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(self.tex_file)
            )
            
            stdout, stderr = process.communicate()
            
          
            base_name = os.path.splitext(os.path.basename(self.tex_file))[0]
            self.log_file = os.path.join(self.output_dir, f"{base_name}.log")
            
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()
                    errors = self._check_log_for_errors(log_content)
                    if errors:
                        error_msg = "\n".join(errors)
                        self.update_status.emit(f"LaTeX Errors Found:\n{error_msg}")
                        return False, error_msg
            
            self.update_progress.emit(40)
            
         
            cmd = [
                'pdflatex',
                '-interaction=nonstopmode',
                '-file-line-error',
                f'-output-directory={self.output_dir}',
                self.tex_file
            ]
            
            self.update_status.emit("Generating PDF...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(self.tex_file)
            )
            
            stdout, stderr = process.communicate()
            self.update_progress.emit(80)
            
         
            self.update_status.emit("Finalizing references...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=os.path.dirname(self.tex_file)
            )
            
            stdout, stderr = process.communicate()
            
            pdf_file = os.path.join(self.output_dir, f"{base_name}.pdf")
            if os.path.exists(pdf_file) and os.path.getsize(pdf_file) > 0:
                self.update_progress.emit(100)
                return True, pdf_file
            else:
                return False, "PDF file was not generated successfully"
                
        except Exception as e:
            return False, str(e)
    
    def run(self):
        """Run the compilation process"""
        try:
            success, result = self._compile_latex()
            
            if success:
                self.update_status.emit(f"PDF generated successfully: {result}")
                self.finished.emit(True, result)
            else:
                self.update_status.emit(f"Error during compilation: {result}")
                self.finished.emit(False, result)
                
        except Exception as e:
            self.update_status.emit(f"System Error: {str(e)}")
            self.finished.emit(False, str(e))


class LatexComponentSelector(QMainWindow):
    """Main GUI application for selecting and printing LaTeX components"""
    
    def __init__(self):
        super().__init__()
        self.parser = None
        self.selected_components = []
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface"""
        self.setWindowTitle('LaTeX Component Selector')
        self.setGeometry(100, 100, 800, 600)
        
     
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
       
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        file_layout = QHBoxLayout()
        self.file_label = QLabel("No file selected")
        file_layout.addWidget(self.file_label)
        
        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_file)
        file_layout.addWidget(self.browse_button)
        
        main_layout.addLayout(file_layout)
        
        self.component_list = QListWidget()
        self.component_list.setSelectionMode(QListWidget.MultiSelection)
        main_layout.addWidget(self.component_list)
        
        self.status_label = QLabel("Ready")
        main_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        button_layout = QHBoxLayout()
        
        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all_components)
        button_layout.addWidget(self.select_all_button)
        
        self.deselect_all_button = QPushButton("Deselect All")
        self.deselect_all_button.clicked.connect(self.deselect_all_components)
        button_layout.addWidget(self.deselect_all_button)
        
        self.generate_button = QPushButton("Generate PDF")
        self.generate_button.clicked.connect(self.generate_pdf)
        self.generate_button.setEnabled(False)
        button_layout.addWidget(self.generate_button)
        
        main_layout.addLayout(button_layout)
        
    def browse_file(self):
        """Browse for a LaTeX file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select LaTeX File", "", "LaTeX Files (*.tex)")
            
        if file_path:
            self.file_label.setText(file_path)
            self.load_components(file_path)
            
    def load_components(self, file_path):
        """Load components from the LaTeX file"""
        self.status_label.setText("Loading components...")
        self.progress_bar.setValue(10)
        
       
        self.parser = LatexParser(file_path)
        
       
        if not self.parser.read_file():
            self.status_label.setText("Error reading file")
            QMessageBox.critical(self, "Error", "Could not read LaTeX file")
            return
            
        self.progress_bar.setValue(40)
        

        if not self.parser.extract_components():
            self.status_label.setText("Error extracting components")
            QMessageBox.critical(self, "Error", "Could not extract components from LaTeX file")
            return
            
        self.progress_bar.setValue(70)
        
       
        self.display_components()
        
        self.status_label.setText("Components loaded. Select items to include in the report.")
        self.progress_bar.setValue(100)
        self.generate_button.setEnabled(True)
        
    def display_components(self):
        """Display components in the list widget"""
        self.component_list.clear()
        
        if not self.parser or not self.parser.components:
            return
            
        for component in self.parser.components:
            item_text = f"{component['type']}: {component['name']}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, component)
            self.component_list.addItem(item)
            
    def select_all_components(self):
        """Select all components"""
        for i in range(self.component_list.count()):
            self.component_list.item(i).setSelected(True)
            
    def deselect_all_components(self):
        """Deselect all components"""
        for i in range(self.component_list.count()):
            self.component_list.item(i).setSelected(False)
            
    def get_selected_components(self):
        """Get selected components"""
        selected_components = []
        for i in range(self.component_list.count()):
            item = self.component_list.item(i)
            if item.isSelected():
                component = item.data(Qt.UserRole)
                selected_components.append(component)
                
        return selected_components
            
    def generate_pdf(self):
        """Generate PDF with selected components"""
        selected_components = self.get_selected_components()
        
        if not selected_components:
            QMessageBox.warning(self, "Warning", "No components selected")
            return
            
       
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory")
            
        if not output_dir:
            return
            
        output_file = os.path.join(output_dir, "custom_report.tex")
        
        self.status_label.setText("Generating custom LaTeX file...")
        self.progress_bar.setValue(10)
        
        if not self.parser.generate_custom_tex(selected_components, output_file):
            self.status_label.setText("Error generating custom LaTeX file")
            QMessageBox.critical(self, "Error", "Could not generate custom LaTeX file")
            return
            
        self.progress_bar.setValue(20)
        
 
        self.compilation_thread = CompilationThread(output_file, output_dir)
        self.compilation_thread.update_status.connect(self.status_label.setText)
        self.compilation_thread.update_progress.connect(self.progress_bar.setValue)
        self.compilation_thread.finished.connect(self.compilation_finished)
        self.compilation_thread.start()
        
    def compilation_finished(self, success, message):
        """Handle compilation finished"""
        if success:
            QMessageBox.information(self, "Success", 
                                   f"PDF generated successfully: {message}")
        else:
            QMessageBox.critical(self, "Error", 
                               f"Error compiling LaTeX: {message}")
            
            
def main():
    app = QApplication(sys.argv)
    main_window = LatexComponentSelector()
    main_window.show()
    sys.exit(app.exec_())
    
    
if __name__ == "__main__":
    main()
