import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { TaskDetailComponent } from './task-detail/task-detail.component';
import { TasksComponent } from './tasks.component';

const routes: Routes = [
  {
    path: ':id/detail',
    component: TaskDetailComponent,
  },
  { path: '', component: TasksComponent },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule],
})
export class TasksRoutingModule {}
