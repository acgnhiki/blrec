import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PathTemplateEditDialogComponent } from './path-template-edit-dialog.component';

describe('PathTemplateEditDialogComponent', () => {
  let component: PathTemplateEditDialogComponent;
  let fixture: ComponentFixture<PathTemplateEditDialogComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ PathTemplateEditDialogComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PathTemplateEditDialogComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
